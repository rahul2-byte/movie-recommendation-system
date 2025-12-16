#!/usr/bin/env python3
"""
Build FAISS indices for all retrieval models (offline).

This script:
- inspects embedding artifacts
- chooses FAISS index types automatically
- builds one index per retriever
- saves indices under indices/<retriever_name>/
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import faiss
from scipy import sparse

# ---------------------------------------------------------
# Logging
# ---------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
LOGGER = logging.getLogger("faiss_index_builder")

# ---------------------------------------------------------
# Paths
# ---------------------------------------------------------
MODELS_DIR = Path("models")
INDICES_DIR = Path("indices")

# ---------------------------------------------------------
# Embedding inspection
# ---------------------------------------------------------
def load_embeddings(path: Path) -> np.ndarray:
    LOGGER.info("Loading embeddings from %s", path)

    if path.suffix == ".npy":
        return np.load(path)

    if path.suffix == ".npz":
        X = sparse.load_npz(path)
        raise ValueError(
            f"Sparse embeddings detected at {path}. "
            "FAISS requires dense vectors. "
            "Apply SVD or densification before indexing."
        )

    raise ValueError(f"Unsupported embedding format: {path}")


def choose_faiss_index(X: np.ndarray) -> faiss.Index:
    if X.dtype != np.float32:
        X = X.astype(np.float32)

    if not X.flags["C_CONTIGUOUS"]:
        X = np.ascontiguousarray(X)

    n, d = X.shape
    LOGGER.info("Embedding shape: n=%d d=%d", n, d)

    if d <= 512:
        LOGGER.info("Using HNSW index")
        index = faiss.IndexHNSWFlat(d, 32)
        index.hnsw.efSearch = 64
    else:
        LOGGER.info("Using IVF Flat index")
        nlist = min(4096, max(64, n // 100))
        quantizer = faiss.IndexFlatIP(d)
        index = faiss.IndexIVFFlat(quantizer, d, nlist, faiss.METRIC_INNER_PRODUCT)
        index.train(X)

    return index


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------
def main() -> None:
    INDICES_DIR.mkdir(parents=True, exist_ok=True)

    for retriever_dir in MODELS_DIR.iterdir():
        if not retriever_dir.is_dir():
            continue

        LOGGER.info("Processing retriever: %s", retriever_dir.name)

        embedding_files = list(retriever_dir.glob("*.npy"))
        if not embedding_files:
            LOGGER.warning("No dense embeddings found, skipping")
            continue

        embeddings = load_embeddings(embedding_files[0])

        index = choose_faiss_index(embeddings)
        index.add(embeddings)

        out_dir = INDICES_DIR / retriever_dir.name
        out_dir.mkdir(parents=True, exist_ok=True)

        faiss.write_index(index, str(out_dir / "faiss.index"))

        LOGGER.info(
            "Index built for %s | vectors=%d",
            retriever_dir.name,
            embeddings.shape[0],
        )


if __name__ == "__main__":
    main()
