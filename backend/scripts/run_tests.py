import logging
import os
import sys
from pathlib import Path

import numpy as np

# Force local path mode for deterministic file checks
os.environ["ENVIRONMENT"] = "LOCAL"

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from common.config import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("run_tests")


def _resolve(path_like: str) -> Path:
    p = Path(str(path_like))
    return p if p.is_absolute() else (BACKEND_ROOT / p)


def _assert_exists(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"{label} missing: {path}")


def test_core_data_files() -> None:
    _assert_exists(_resolve(config.system.movies_metadata_path), "movies metadata")
    _assert_exists(_resolve(config.system.ratings_path), "ratings parquet")
    _assert_exists(_resolve(config.system.tags_path), "tags parquet")


def test_retrieval_artifacts() -> None:
    artifacts = config.system.retrieval_artifacts
    for name in ["tfidf", "content_based", "als", "two_tower"]:
        cfg = getattr(artifacts, name)
        emb = _resolve(cfg.embeddings_path)
        idx = _resolve(cfg.faiss_index_path)
        id_map = _resolve(cfg.id_map_path)

        _assert_exists(emb, f"{name} embeddings")
        _assert_exists(idx, f"{name} faiss index")
        _assert_exists(id_map, f"{name} id map")

        # Basic shape sanity check
        arr = np.load(emb)
        if arr.size == 0:
            raise ValueError(f"{name} embeddings are empty: {emb}")


def test_ranker_artifact() -> None:
    ranker_path = _resolve(config.system.ranker_model_dir) / "lgbm_lambdarank.txt"
    _assert_exists(ranker_path, "ranker model")
    if ranker_path.stat().st_size == 0:
        raise ValueError(f"ranker model is empty: {ranker_path}")


def main() -> None:
    log.info("Running backend script smoke tests...")
    test_core_data_files()
    test_retrieval_artifacts()
    test_ranker_artifact()
    log.info("All smoke tests passed.")


if __name__ == "__main__":
    main()
