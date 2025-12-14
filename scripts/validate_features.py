#!/usr/bin/env python3
"""
Feature Validation Script (FINAL)

Validates:
- Schema & shape
- Data types
- Missing values (feature-aware)
- Distribution checks (non-embedding only)
- Outlier detection (non-PCA only)
- Duplicate ID checks
- Embedding dimensionality
- Feature group inventory
- Feature count sanity checks

Run AFTER build_all_features.py
"""

import argparse
import logging
from pathlib import Path
import sys
import numpy as np
import pandas as pd

# ---------------------------------------------------------
# Path setup
# ---------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from features.config import USER_FEATURES_PQ, ITEM_FEATURES_PQ

# ---------------------------------------------------------
# Logging
# ---------------------------------------------------------
logger = logging.getLogger("validate_features")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(levelname)s] %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------
def load_df(path: str) -> pd.DataFrame:
    logger.info(f"Loading: {path}")
    return pd.read_parquet(path)


def check_schema(df: pd.DataFrame, name: str):
    logger.info(f"\n🔍 Schema: {name}")
    logger.info(f"  Rows: {df.shape[0]:,}")
    logger.info(f"  Columns: {df.shape[1]:,}")


def check_dtypes(df: pd.DataFrame, name: str):
    logger.info(f"\n📦 Data types: {name}")
    for col, dt in df.dtypes.items():
        logger.info(f"  {col}: {dt}")


def check_unique_ids(df: pd.DataFrame, name: str, id_col: str):
    logger.info(f"\n🆔 ID uniqueness: {name}")

    if id_col not in df.columns:
        logger.error(f"❌ Missing ID column: {id_col}")
        return

    dup = df[id_col].duplicated().sum()
    if dup > 0:
        logger.warning(f"⚠ {dup} duplicate IDs found")
    else:
        logger.info("✔ ID column is unique")


def check_missing_values(df: pd.DataFrame, name: str):
    logger.info(f"\n🚫 Missing value check: {name}")

    missing = df.isna().sum()
    missing = missing[missing > 0]

    if missing.empty:
        logger.info("✔ No missing values detected")
        return

    logger.warning("⚠ Missing values detected:")
    for col, cnt in missing.items():
        logger.warning(f"  {col}: {cnt}")


def check_distribution(df: pd.DataFrame, name: str):
    """
    Distribution stats ONLY for non-embedding numeric features.
    """
    logger.info(f"\n📊 Distribution stats: {name}")

    numeric_cols = df.select_dtypes(include=[np.number]).columns

    excluded_prefixes = ("title_pca_", "tag_pca_")
    cols = [c for c in numeric_cols if not c.startswith(excluded_prefixes)]

    if not cols:
        logger.info("No non-embedding numeric columns")
        return

    stats = df[cols].describe().T
    logger.info(stats.to_string())


def detect_outliers(df: pd.DataFrame, name: str, z_thresh: float = 4.0):
    """
    Outlier detection ONLY for non-embedding numeric features.
    """
    logger.info(f"\n⚠ Outlier detection (z>{z_thresh}): {name}")

    num_cols = df.select_dtypes(include=[np.number]).columns
    num_cols = [
        c for c in num_cols
        if not c.startswith(("title_pca_", "tag_pca_"))
    ]

    if not num_cols:
        logger.info("No eligible columns for outlier detection")
        return

    z = np.abs((df[num_cols] - df[num_cols].mean()) / df[num_cols].std())
    counts = (z > z_thresh).sum()

    flagged = False
    for col, cnt in counts.items():
        if cnt > 0:
            logger.warning(f"  {col}: {cnt} outliers")
            flagged = True

    if not flagged:
        logger.info("✔ No significant outliers")


def check_embedding_groups(df: pd.DataFrame, name: str):
    logger.info(f"\n🧠 Embedding groups: {name}")

    groups = {
        "title_pca_": "Title embedding",
        "tag_pca_": "Tag embedding",
        "genre__": "Genre one-hot",
        "movie_rating_": "Rating aggregates",
    }

    for prefix, label in groups.items():
        cols = [c for c in df.columns if c.startswith(prefix)]
        if cols:
            logger.info(f"  {label}: {len(cols)} dims")
        else:
            logger.warning(f"  ⚠ Missing group: {label}")


def feature_inventory(df: pd.DataFrame, name: str):
    logger.info(f"\n📋 Feature inventory: {name}")

    groups = {}
    for col in df.columns:
        prefix = col.split("_")[0]
        groups.setdefault(prefix, 0)
        groups[prefix] += 1

    for k, v in sorted(groups.items()):
        logger.info(f"  {k}: {v} features")

    logger.info(f"  TOTAL FEATURES: {df.shape[1]}")


# ---------------------------------------------------------
# Main validation
# ---------------------------------------------------------
def validate(user_features_path: str, item_features_path: str):
    logger.info("=" * 42)
    logger.info("🔎 Starting Feature Validation")
    logger.info("=" * 42)

    user_df = load_df(user_features_path)
    item_df = load_df(item_features_path)

    # ---------------- USER ----------------
    check_schema(user_df, "User Features")
    check_dtypes(user_df, "User Features")
    check_missing_values(user_df, "User Features")
    check_unique_ids(user_df, "User Features", "userId")
    check_distribution(user_df, "User Features")
    detect_outliers(user_df, "User Features")
    feature_inventory(user_df, "User Features")

    # ---------------- ITEM ----------------
    check_schema(item_df, "Item Features")
    check_dtypes(item_df, "Item Features")
    check_missing_values(item_df, "Item Features")
    check_unique_ids(item_df, "Item Features", "movieId")
    check_distribution(item_df, "Item Features")
    detect_outliers(item_df, "Item Features")
    check_embedding_groups(item_df, "Item Features")
    feature_inventory(item_df, "Item Features")

    logger.info("=" * 42)
    logger.info("🎉 Feature validation completed successfully!")
    logger.info("=" * 42)


# ---------------------------------------------------------
# CLI
# ---------------------------------------------------------
def parse_args():
    parser = argparse.ArgumentParser("Validate feature parquet files")
    parser.add_argument("--user_features", type=str, default=USER_FEATURES_PQ)
    parser.add_argument("--item_features", type=str, default=ITEM_FEATURES_PQ)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    validate(args.user_features, args.item_features)
