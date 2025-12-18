"""
Unified ALS Training + Embedding Export Script
=============================================

Purpose:
- Single entry-point to train ALS model
- Produces FAISS-ready item + user embeddings
- Handles ALS zero-interaction items correctly
- Enforces strict embedding ↔ ID mapping contract

Artifacts written:
models/als/
    - item_embeddings.npy
    - user_embeddings.npy
    - item_id_map.json
    - user_id_map.json
    - metadata.json
"""

import logging
import sys
import traceback
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

    if not path.exists():
        raise FileNotFoundError(f"Ratings file not found: {path}")

    df = pd.read_csv(path)

    required_cols = {"userId", "movieId", "rating"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    if df.empty:
        raise ValueError("Ratings file is empty")

    return df


# ---------------------------------------------------------------------
# ID Remapping (SOURCE OF TRUTH)
# ---------------------------------------------------------------------
def remap_ids(
    df: pd.DataFrame,
) -> Tuple[pd.DataFrame, int, int, List[int], List[int]]:
    """
    Remap userId/movieId → contiguous indices.

    NOTE:
    item_id_map here represents the FULL catalog.
    ALS will later learn factors for only a subset.
    """

    logger.info("Remapping user and item IDs")

    df = df.copy()

    user_codes = pd.Categorical(df["userId"])
    item_codes = pd.Categorical(df["movieId"])

    if user_codes.categories.empty or item_codes.categories.empty:
        raise ValueError("No users or items after factorization")

    df["user_idx"] = user_codes.codes.astype(np.int32)
    df["item_idx"] = item_codes.codes.astype(np.int32)

    num_users = len(user_codes.categories)
    num_items = len(item_codes.categories)

    user_id_map: List[int] = user_codes.categories.tolist()
    item_id_map: List[int] = item_codes.categories.tolist()

    logger.info("num_users=%d num_items=%d", num_users, num_items)

    return df, num_users, num_items, item_id_map, user_id_map

def filter_active_entities(df: pd.DataFrame) -> pd.DataFrame:
    """
    Keep only users and items with at least one interaction.
    """
    item_counts = df.groupby("movieId").size()
    user_counts = df.groupby("userId").size()

    valid_items = item_counts[item_counts > 0].index
    valid_users = user_counts[user_counts > 0].index

    df = df[
        df["movieId"].isin(valid_items)
        & df["userId"].isin(valid_users)
    ].reset_index(drop=True)

    return df


def remap_ids(
    df: pd.DataFrame,
) -> Tuple[pd.DataFrame, List[int], List[int]]:
    """
    Remap IDs AFTER filtering.
    This mapping is now ALS-safe forever.
    """
    user_codes = pd.Categorical(df["userId"])
    item_codes = pd.Categorical(df["movieId"])

    df["user_idx"] = user_codes.codes.astype(np.int32)
    df["item_idx"] = item_codes.codes.astype(np.int32)

    user_id_map = user_codes.categories.tolist()
    item_id_map = item_codes.categories.tolist()

    return df, user_id_map, item_id_map



# ---------------------------------------------------------------------
# Training Pipeline
# ---------------------------------------------------------------------
def train_als() -> None:
    ratings = load_ratings(RATINGS_PATH)

    # -------------------------------------------------
    # 1. FILTER (ALS CANNOT HANDLE ZERO-DEGREE ENTITIES)
    # -------------------------------------------------
    ratings = ratings[
        ratings["userId"].notna() & ratings["movieId"].notna()
    ]

    # -------------------------------------------------
    # 2. REMAP AFTER FILTERING (AUTHORITATIVE)
    # -------------------------------------------------
    user_codes = pd.Categorical(ratings["userId"])
    item_codes = pd.Categorical(ratings["movieId"])

    ratings["user_idx"] = user_codes.codes.astype(np.int32)
    ratings["item_idx"] = item_codes.codes.astype(np.int32)

    user_id_map = user_codes.categories.tolist()
    item_id_map = item_codes.categories.tolist()

    num_users = len(user_id_map)
    num_items = len(item_id_map)

    logger.info("ALS users=%d items=%d", num_users, num_items)

    # -------------------------------------------------
    # 3. BUILD ITEM × USER MATRIX (THIS IS THE FIX)
    # -------------------------------------------------
    # Shape: (num_items, num_users)
    interactions = sp.coo_matrix(
        (
            ratings["rating"].to_numpy(np.float32),
            (ratings["item_idx"], ratings["user_idx"]),
        ),
        shape=(num_items, num_users),
    ).tocsr()

    if interactions.nnz == 0:
        raise RuntimeError("ALS interaction matrix is empty")

    # -------------------------------------------------
    # 4. TRAIN ALS (NO TRANSPOSE EVER)
    # -------------------------------------------------
    trainer = ALSModelTrainer(
        ALSConfig(
            factors=128,
            iterations=20,
            regularization=0.05,
            alpha=40.0,
            use_gpu=False,
        )
    )

    trainer.train(interactions)

    # -------------------------------------------------
    # 5. HARD GUARANTEES (NOW THEY HOLD)
    # -------------------------------------------------
    assert trainer.model.item_factors.shape[0] == num_items, (
        trainer.model.item_factors.shape,
        num_items,
    )
    assert trainer.model.user_factors.shape[0] == num_users, (
        trainer.model.user_factors.shape,
        num_users,
    )

    # -------------------------------------------------
    # 6. SAVE (FAISS-SAFE, FINAL)
    # -------------------------------------------------
    trainer.save(
        output_dir=MODEL_DIR,
        item_id_map=item_id_map,
        user_id_map=user_id_map,
    )

    logger.info("ALS training + export completed successfully")


# ---------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------
if __name__ == "__main__":
    try:
        train_als()
    except Exception as e:
        logger.error("ALS pipeline failed: %s", e)
        traceback.print_exc()
        sys.exit(1)
