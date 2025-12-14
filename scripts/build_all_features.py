#!/usr/bin/env python3
"""
Master feature-building script.

This script orchestrates the FULL feature engineering pipeline:
1. Build interaction-level features
2. Build user-level features
3. Build item-level features

Output is written into:
    data/processed/features/

This script:
- Is GPU-friendly (uses cudf automatically if available)
- Is fully vectorized (no loops)
- Logs progress
- Handles missing columns gracefully
- Can run as a standalone pipeline or part of Airflow/Prefect/Kubeflow

Usage:
    python scripts/build_all_features.py \
        --ratings data/raw/ratings.csv \
        --movies data/raw/movies.csv
"""

import argparse
import logging
import os
import sys
from pathlib import Path

# Add project root to PYTHONPATH
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from features.config import (
    FEATURE_DIR,
    USER_FEATURES_PQ,
    ITEM_FEATURES_PQ,
)

from features.build_user_features import build_user_features
from features.build_item_features import build_item_features

# ---------------------------------------------------------
# Logging Setup
# ---------------------------------------------------------
logger = logging.getLogger("build_features")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)


# ---------------------------------------------------------
# Build Pipeline
# ---------------------------------------------------------
def build_all_features(
    ratings_path: str,
    movies_path: str,
    tags_path: str,
    out_dir: str,
):
    """
    End-to-end feature building pipeline.

    Args:
        ratings_path: path to ratings.csv (or parquet)
        movies_path: path to movies.csv
        out_dir: directory where parquet outputs will be saved
    """

    logger.info("=================================================")
    logger.info("🚀 Starting FULL Feature Engineering Pipeline")
    logger.info("=================================================")

    os.makedirs(out_dir, exist_ok=True)

    logger.info("Interaction features complete.")
    # logger.info(f"Saved to: {INTERACTION_FEATURES_PQ}")

    # ------------------------------
    # 1) User-level features
    # ------------------------------
    logger.info("Step 1: Building user features...")

    user_df = build_user_features(
        interactions_path=ratings_path,
        out_path=str(Path(out_dir) / Path(USER_FEATURES_PQ).name),
        user_col="userId",
        rating_col="rating",
    )

    logger.info("User features complete.")
    logger.info(f"Saved to: {Path(out_dir) / Path(USER_FEATURES_PQ).name}")

    # ------------------------------
    # 2) Item-level features
    # ------------------------------
    logger.info("Step 2: Building item features...")

    item_df = build_item_features(
    interactions_path=ratings_path,
    movies_path=movies_path,
    tags_path=tags_path,
    out_path=str(Path(out_dir) / Path(ITEM_FEATURES_PQ).name),
    out_dir=out_dir,   # to save embeddings
    item_col="movieId",
    rating_col="rating",
    time_col="timestamp",
    )

    logger.info("Item features complete.")
    logger.info(f"Saved to: {ITEM_FEATURES_PQ}")

    logger.info("=================================================")
    logger.info("🎉 Feature Engineering Pipeline Finished Successfully!")
    logger.info("=================================================")

    return user_df, item_df


def parse_args():
    """
    Debug-friendly version of parse_args().
    Does NOT read command line arguments.
    Returns a simple namespace with predefined parameters.
    """

    class Args:
        pass

    args = Args()

    # 🔧 Set your debug paths here
    args.ratings = "data/raw/ratings.csv"      
    args.movies  = "data/raw/movies.csv"  
    args.tags = "data/raw/tags.csv"
    args.out_dir = str(FEATURE_DIR)
    return args



if __name__ == "__main__":
    args = parse_args()

    build_all_features(
        ratings_path=args.ratings,
        movies_path=args.movies,
        tags_path=args.tags,
        out_dir=args.out_dir,
    )
