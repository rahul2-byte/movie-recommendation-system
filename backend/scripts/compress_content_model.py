#!/usr/bin/env python3
import sys
import time
from pathlib import Path

import faiss
import joblib
import numpy as np
from loguru import logger
from sklearn.decomposition import PCA

# Configuration
BACKEND_ROOT = Path(__file__).resolve().parent.parent
INPUT_DIR = BACKEND_ROOT / "artifacts" / "models" / "content_based"
OUTPUT_DIR = BACKEND_ROOT / "artifacts" / "models" / "content_based_compressed"
TARGET_DIM = 64  # Compressing to 64 dimensions (same as ALS/Two-Tower)

logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | <level>{message}</level>",
)


def compress_model():
    if not INPUT_DIR.exists():
        logger.error(f"Input directory not found: {INPUT_DIR}")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    start_time = time.time()

    # 1. Load Embeddings
    embeddings_path = INPUT_DIR / "item_embeddings.npy"
    logger.info(f"Loading embeddings from {embeddings_path}...")
    try:
        embeddings = np.load(embeddings_path)
        original_dim = embeddings.shape[1]
        logger.info(
            f"Original shape: {embeddings.shape} ({embeddings.nbytes / 1024**3:.2f} GB)"
        )
    except Exception as e:
        logger.error(f"Failed to load embeddings: {e}")
        return

    # 2. Train PCA and Transform
    logger.info(
        f"Fitting PCA to reduce dimensions from {original_dim} -> {TARGET_DIM}..."
    )
    pca = PCA(n_components=TARGET_DIM)

    # Check for NaNs/Infs
    if not np.all(np.isfinite(embeddings)):
        logger.warning("Embeddings contain NaNs or Infs. Replacing with zeros.")
        embeddings = np.nan_to_num(embeddings)

    reduced_embeddings = pca.fit_transform(embeddings)

    # Normalize vectors (crucial for Cosine Similarity via L2/IP)
    logger.info("Normalizing reduced vectors...")
    norm = np.linalg.norm(reduced_embeddings, axis=1, keepdims=True)
    # Avoid division by zero
    reduced_embeddings = np.divide(
        reduced_embeddings, norm, out=np.zeros_like(reduced_embeddings), where=norm != 0
    )

    compressed_size_gb = reduced_embeddings.nbytes / 1024**3
    logger.info(
        f"Compressed shape: {reduced_embeddings.shape} ({compressed_size_gb:.2f} GB)"
    )
    logger.success(
        f"Size reduction: {(1 - reduced_embeddings.nbytes / embeddings.nbytes) * 100:.1f}%"
    )

    # 3. Save Compressed Embeddings
    out_emb_path = OUTPUT_DIR / "item_embeddings.npy"
    np.save(out_emb_path, reduced_embeddings.astype(np.float32))
    logger.info(f"Saved compressed embeddings to {out_emb_path}")

    # 4. Rebuild FAISS Index
    logger.info("Rebuilding FAISS index...")
    # Using IndexFlatL2 on normalized vectors is equivalent to Cosine Similarity
    index = faiss.IndexFlatL2(TARGET_DIM)
    index.add(reduced_embeddings.astype(np.float32))

    out_index_path = OUTPUT_DIR / "faiss.index"
    faiss.write_index(index, str(out_index_path))
    logger.info(f"Saved new FAISS index to {out_index_path}")

    # 5. Copy Metadata (id mapping)
    # We copy this unchanged as the IDs correspond to the row indices
    id_map_path = INPUT_DIR / "movie_id_to_idx.json"
    if id_map_path.exists():
        import shutil

        shutil.copy(id_map_path, OUTPUT_DIR / "movie_id_to_idx.json")
        logger.info(f"Copied ID mapping to {OUTPUT_DIR}")
    else:
        logger.warning("movie_id_to_idx.json not found! You might need it.")

    # 6. Save PCA Model (Optional but good for debugging/inference if needed later)
    # We save it just in case, though usually inference uses the pre-computed vectors.
    joblib.dump(pca, OUTPUT_DIR / "pca_model.joblib")

    elapsed = time.time() - start_time
    logger.success(f"Compression complete in {elapsed:.1f}s! 🚀")
    logger.info(f"New artifacts are in: {OUTPUT_DIR}")


if __name__ == "__main__":
    compress_model()
