import logging
import os
import shutil
import subprocess
from pathlib import Path

import pandas as pd

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
FULL_DATA_DIR = BACKEND_DIR / "data" / "processed"
TEST_DATA_DIR = BACKEND_DIR / "data" / "test_mini"


def run_command(cmd, cwd=None):
    log.info(f"Running: {cmd}")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(BACKEND_DIR)
    subprocess.run(cmd, shell=True, check=True, cwd=cwd or str(PROJECT_ROOT), env=env)


def main():
    log.info("--- Starting Mini Pipeline Test (100 Movies) ---")

    # 1. Subsample Data
    if TEST_DATA_DIR.exists():
        shutil.rmtree(TEST_DATA_DIR)
    TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)
    (TEST_DATA_DIR / "raw").mkdir(parents=True, exist_ok=True)

    log.info("Subsampling data files...")
    # Movies (THE TRUTH)
    movies_df = pd.read_parquet(FULL_DATA_DIR / "movies_enriched.parquet").head(100)
    valid_ids = set(movies_df["movie_id"].unique())
    movies_df.to_parquet(TEST_DATA_DIR / "movies_enriched.parquet", index=False)

    # Ratings
    ratings_df = pd.read_parquet(FULL_DATA_DIR / "ratings.parquet")
    ratings_df = ratings_df[ratings_df["movieId"].isin(valid_ids)].head(
        1000
    )  # Small ratings
    ratings_df.to_parquet(TEST_DATA_DIR / "ratings.parquet", index=False)

    # Tags
    tags_df = pd.read_parquet(FULL_DATA_DIR / "tags.parquet")
    tags_df = tags_df[tags_df["movieId"].isin(valid_ids)].head(500)
    tags_df.to_parquet(TEST_DATA_DIR / "tags.parquet", index=False)

    # 2. Swap paths in system.yml temporarily
    sys_yml = BACKEND_DIR / "configs" / "system.yml"
    sys_yml_bak = BACKEND_DIR / "configs" / "system.yml.bak"
    shutil.copy(sys_yml, sys_yml_bak)

    with open(sys_yml) as f:
        content = f.read()

    # Correct substitution logic to match current system.yml
    new_content = content.replace('data_root: "data"', f'data_root: "{TEST_DATA_DIR}"')
    new_content = new_content.replace("${data_root}/processed", "${data_root}")

    with open(sys_yml, "w") as f:
        f.write(new_content)

    try:
        # 3. Standardize Metadata
        run_command("python3 backend/scripts/finalize_metadata.py")

        # 4. Run Preparation
        # (This will generate mini sequences and mini ranking dataset)
        run_command("python3 backend/scripts/prepare_data.py")

        # 5. Run Training
        # Clean both the final artifacts AND the intermediate ranking fragments
        run_command("rm -rf backend/artifacts/native/*")
        run_command(f"rm -rf {BACKEND_DIR}/training/ranking/native/rank.*")
        run_command("python3 backend/scripts/run_native_training.py")

        log.info("Mini test completed successfully!")

    finally:
        # Restore system.yml
        shutil.move(sys_yml_bak, sys_yml)


if __name__ == "__main__":
    main()
