import logging
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Add backend to path to allow imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
log = logging.getLogger(__name__)

from common.config import config

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
NATIVE_FEATURES_DIR = BACKEND_DIR / "features" / "native"


def run_command(cmd, cwd=None):
    if cwd is None:
        cwd = str(PROJECT_ROOT)
    log.info(f"Executing: {cmd} in {cwd}")
    subprocess.run(cmd, shell=True, check=True, cwd=cwd)


def main():
    log.info("--- [Python] Starting Optimized Data Preparation ---")

    # 1. Cleaning & Filtering
    log.info("Step 1/5: Cleaning data against enriched movies...")
    # Resolve relative to backend service root
    movies_path = BACKEND_DIR / str(config.system.movies_metadata_path)
    ratings_path = BACKEND_DIR / str(config.system.ratings_path)
    tags_path = BACKEND_DIR / str(config.system.tags_path)

    if not movies_path.exists():
        log.error(f"Enriched movies not found at {movies_path}")
        return

    movies_df = pd.read_parquet(movies_path)
    valid_movie_ids = set(movies_df["movie_id"].unique())
    log.info(f"Loaded {len(valid_movie_ids)} valid enriched movies.")

    # Filter Ratings
    ratings_df = pd.read_parquet(ratings_path)
    original_count = len(ratings_df)
    ratings_df = ratings_df[ratings_df["movieId"].isin(valid_movie_ids)]
    ratings_df.to_parquet(ratings_path, index=False)
    log.info(f"Ratings filtered: {original_count} -> {len(ratings_df)}")

    # 2. Compile C++ Helper Tools
    log.info("Step 2/5: Compiling C++ feature tools...")
    run_command("make clean && make", cwd=str(NATIVE_FEATURES_DIR))

    # 3. Generate Sequences
    log.info("Step 3/5: Generating training sequences...")
    run_command(f"python3 {NATIVE_FEATURES_DIR}/run_sequences.py", cwd=str(BACKEND_DIR))

    # 4. Generate Ranking Dataset
    log.info("Step 4/5: Generating ranking features...")
    run_command(
        f"python3 {NATIVE_FEATURES_DIR}/run_ranker_gen.py", cwd=str(BACKEND_DIR)
    )

    # 5. Export for C++ Training
    log.info("Step 5/6: Exporting files for native C++ training...")
    raw_dir = BACKEND_DIR / str(config.system.data_root) / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    log.info(f"Exporting ratings.csv to {raw_dir}...")
    ratings_df.to_csv(raw_dir / "ratings.csv", index=False)

    log.info("Exporting movies.csv...")
    simple_movies = pd.DataFrame(
        {
            "movieId": movies_df["movie_id"],
            "title": movies_df["title"]
            + " ("
            + movies_df["release_year"].fillna(0).astype(int).astype(str)
            + ")",
            "genres": movies_df["genres"].apply(
                lambda x: "|".join(x) if isinstance(x, (list, np.ndarray)) else ""
            ),
        }
    )
    simple_movies.to_csv(raw_dir / "movies.csv", index=False)

    log.info("Exporting tags.csv...")
    tags_df = pd.read_parquet(tags_path)
    tags_df = tags_df[tags_df["movieId"].isin(valid_movie_ids)]
    tags_df.to_csv(raw_dir / "tags.csv", index=False)

    # 6. Binary Dump for Optimized Two-Tower
    log.info("Step 6/6: Creating Optimized Binary Datasets (Zero-Copy)...")
    run_command(
        f"python3 {NATIVE_FEATURES_DIR}/dump_binary_data.py", cwd=str(BACKEND_DIR)
    )

    log.info("--- [Python] Data preparation complete! ---")


if __name__ == "__main__":
    main()
