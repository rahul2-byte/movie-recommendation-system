"""
Unified ALS Training + Embedding Export Script
=============================================

Purpose:
- Single entry-point to train ALS model
- Produces FAISS-ready item embeddings
- Enforces global embedding contract

Artifacts written:
models/als/
    - item_embeddings.npy
    - item_id_map.json
    - metadata.json
"""

import logging
from pathlib import Path
from typing import Tuple, List

import numpy as np
import pandas as pd
import scipy.sparse as sp

from retrieval.als import ALSConfig, ALSModelTrainer

# ---------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("scripts.train_als")

# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------
DATA_DIR = Path("data/raw")
MODEL_DIR = Path("models/als")

RATINGS_PATH = DATA_DIR / "ratings.csv"

# ---------------------------------------------------------------------
# Data Loading
# ---------------------------------------------------------------------
def load_ratings(path: Path) -> pd.DataFrame:
    logger.info("Loading ratings from %s", path)

    df = pd.read_csv(path)

    required_cols = {"userId", "movieId", "rating"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    return df


# ---------------------------------------------------------------------
# ID Remapping (SOURCE OF TRUTH)
# ---------------------------------------------------------------------
def remap_ids(
    df: pd.DataFrame,
) -> Tuple[pd.DataFrame, int, int, List[int]]:
    """
    Remap userId/movieId → contiguous indices.

    Returns:
        df: DataFrame with user_idx, item_idx
        num_users: number of unique users
        num_items: number of unique items
        item_id_map: index → original movieId
    """
    logger.info("Remapping user and item IDs")

    df = df.copy()

    user_codes = pd.Categorical(df["userId"])
    item_codes = pd.Categorical(df["movieId"])

    df["user_idx"] = user_codes.codes.astype("int64")
    df["item_idx"] = item_codes.codes.astype("int64")

    num_users = len(user_codes.categories)
    num_items = len(item_codes.categories)

    # CRITICAL: index → original movieId
    item_id_map: List[int] = item_codes.categories.tolist()

    logger.info("num_users=%d num_items=%d", num_users, num_items)

    return df, num_users, num_items, item_id_map


# ---------------------------------------------------------------------
# Training Pipeline
# ---------------------------------------------------------------------
def train_als() -> None:
    """
    End-to-end ALS pipeline.

    Steps:
    1. Load ratings
    2. Remap IDs (authoritative)
    3. Build CSR interaction matrix
    4. Train ALS
    5. Export embeddings + ID map + metadata
    """

    # ---------------------------
    # Load & preprocess
    # ---------------------------
    ratings = load_ratings(RATINGS_PATH)
    ratings, num_users, num_items, item_id_map = remap_ids(ratings)

    # ---------------------------
    # Build interaction matrix
    # ---------------------------
    config = ALSConfig(
        factors=128,
        iterations=20,
        regularization=0.05,
        alpha=40.0,
        use_gpu=False,
    )

    trainer = ALSModelTrainer(config)

    interactions: sp.csr_matrix = trainer.build_interaction_matrix(
        user_idx=ratings["user_idx"].to_numpy(dtype=np.int32),
        item_idx=ratings["item_idx"].to_numpy(dtype=np.int32),
        values=ratings["rating"].to_numpy(dtype=np.float32),
        num_users=num_users,
        num_items=num_items,
        dtype=np.float32,
    )

    # ---------------------------
    # Train
    # ---------------------------
    trainer.train(interactions)

    # ---------------------------
    # Export (FAISS-safe contract)
    # ---------------------------
    trainer.save(
        output_dir=MODEL_DIR,
        item_id_map=item_id_map,
    )

    logger.info("ALS training + export completed successfully")


# ---------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------
if __name__ == "__main__":
    train_als()
