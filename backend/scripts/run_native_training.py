import logging
import os
import subprocess
import sys
from pathlib import Path

# Add backend to path to allow imports

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


from common.config import config

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

log = logging.getLogger(__name__)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT

TRAINING_DIR = PROJECT_ROOT / "training"

BIN_DIR = TRAINING_DIR / "bin"

ARTIFACTS_DIR = PROJECT_ROOT / "artifacts" / "native"


def run_command(cmd, cwd=None, env=None):
    if cwd is None:
        cwd = str(PROJECT_ROOT)

    # Ensure PYTHONPATH is set so sub-scripts find 'common'
    if env is None:
        env = os.environ.copy()

    if "PYTHONPATH" not in env:
        env["PYTHONPATH"] = str(PROJECT_ROOT)
    else:
        env["PYTHONPATH"] = f"{PROJECT_ROOT}:{env['PYTHONPATH']}"

    # Force single-threaded BLAS to avoid OpenMP conflict in Two-Tower training
    env["OPENBLAS_NUM_THREADS"] = "1"
    env["MKL_NUM_THREADS"] = "1"
    env["VECLIB_MAXIMUM_THREADS"] = "1"
    env["NUMEXPR_NUM_THREADS"] = "1"

    log.info(f"Executing: {cmd} in {cwd}")
    subprocess.run(cmd, shell=True, check=True, cwd=cwd, env=env)


def main():
    log.info("--- [C++] Starting Central Native Training Pipeline ---")
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    # Resolve paths from config for C++ args
    data_root = PROJECT_ROOT / str(config.system.data_root)
    raw_dir = data_root / "raw"

    movies_csv = str(raw_dir / "movies.csv")
    ratings_csv = str(raw_dir / "ratings.csv")
    tags_csv = str(raw_dir / "tags.csv")
    out_dir = str(PROJECT_ROOT / "artifacts" / "native") + "/"

    # 1. Compilation
    log.info("Step 1/7: Compiling native training tools...")
    run_command("make clean && make", cwd=str(TRAINING_DIR))

    # 2. Train ALS (Retrieval)
    if not (ARTIFACTS_DIR / "als_item_embeddings.bin").exists():
        log.info("Step 2/7: Training ALS model (Collaborative Filtering)...")
        als_cmd = (
            f"python3 training/retrieval/native/als_bridge.py | {BIN_DIR}/train_als"
        )
        run_command(als_cmd)
    else:
        log.info("Step 2/7: ALS artifacts found, skipping.")

    # 3. Train Content-Based (Retrieval)
    if not (ARTIFACTS_DIR / "content_embeddings.bin").exists():
        log.info("Step 3/7: Training Content-Based model (Dense Metadata)...")
        # Args: movies_path, ratings_path, tags_path, output_dir
        run_command(
            f"{BIN_DIR}/train_content {movies_csv} {ratings_csv} {tags_csv} {out_dir}"
        )
    else:
        log.info("Step 3/7: Content-Based artifacts found, skipping.")

    # 4. Train TF-IDF (Retrieval)
    if not (ARTIFACTS_DIR / "tfidf_matrix.bin").exists():
        log.info("Step 4/7: Training TF-IDF model (Sparse Genres)...")
        # Args: movies_path, output_dir
        run_command(f"{BIN_DIR}/train_tfidf {movies_csv} {out_dir}")
    else:
        log.info("Step 4/7: TF-IDF artifacts found, skipping.")

    # 5. Prepare Ranking Data
    if not list(Path(TRAINING_DIR / "ranking" / "native").glob("*.train")):
        log.info("Step 5/7: Preparing Ranking Data (Parquet -> LGBM CSV)...")
        input_parquet = PROJECT_ROOT / str(config.system.training_dataset_path)
        output_prefix = TRAINING_DIR / "ranking" / "native" / "rank"
        run_command(f"{BIN_DIR}/converter {input_parquet} {output_prefix}")
    else:
        log.info("Step 5/7: Ranking data fragments found, skipping.")

    # 6. Train Ranking Model (LightGBM)
    log.info("Step 6/7: Training Ranking Model (LightGBM Out-of-Core)...")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT)
    run_command("python3 training/ranking/train_from_csv.py", env=env)

    # 7. Train Two-Tower (Retrieval)
    if not (ARTIFACTS_DIR / "two_tower_embeddings.bin").exists():
        log.info("Step 7/7: Training Two-Tower model (Neural Sparse)...")
        # Args: binary_base_dir, output_dir
        binary_dir = str(PROJECT_ROOT / "data" / "binary_cache") + "/"
        run_command(f"{BIN_DIR}/train_two_tower {binary_dir} {out_dir}")
    else:
        log.info("Step 7/7: Two-Tower artifacts found, skipping.")

    # 8. Organize Artifacts for Production
    log.info("Step 8/9: Organizing Models for Production...")
    MODELS_DIR = BACKEND_DIR / "artifacts" / "models"
    RETRIEVAL_DIR = MODELS_DIR / "retrieval"
    RANKING_DIR = MODELS_DIR / "ranking"

    RETRIEVAL_DIR.mkdir(parents=True, exist_ok=True)
    RANKING_DIR.mkdir(parents=True, exist_ok=True)

    import shutil

    # Map native artifacts to production names
    # Retrieval
    artifacts_map = {
        "als_item_embeddings.bin": "als.bin",
        "content_embeddings.bin": "content.bin",
        "tfidf_matrix.bin": "tfidf.bin",
        "two_tower_embeddings.bin": "two_tower.bin",
        "als_movie_ids.txt": "als_ids.txt",
        "content_movie_ids.txt": "content_ids.txt",
        "tfidf_movie_ids.txt": "tfidf_ids.txt",
        "tfidf_vocab.txt": "tfidf_vocab.txt",
    }

    for src_name, dst_name in artifacts_map.items():
        src = ARTIFACTS_DIR / src_name
        if src.exists():
            shutil.copy2(src, RETRIEVAL_DIR / dst_name)

    # Ranking
    src_ranker = MODELS_DIR / "ranker" / "lgbm_lambdarank.txt"
    if src_ranker.exists():
        shutil.copy2(src_ranker, RANKING_DIR / "lgbm_ranker.txt")

    log.info(f"Models organized in {MODELS_DIR}")

    # 9. Regenerate runtime retrieval artifacts (FAISS + movie_id_to_idx.json)
    # from the latest native outputs to avoid stale mappings in artifacts/models/*.
    log.info("Step 9/9: Finalizing retrieval artifacts for runtime...")
    run_command("python3 scripts/finalize_artifacts.py")

    log.info("--- [C++] Central Native Training Pipeline Complete! ---")


if __name__ == "__main__":
    main()
