# features/build_user_features.py
"""
Compute user-level aggregated features (interaction-based).

Features produced:
- user_rating_count (int32)
- user_rating_mean (float32)
- user_rating_std (float32)

Removed:
- user_recency_days
- user_last_ts
- user_active_7d / 30d
- timestamp-based/sequence-derived features
"""

from __future__ import annotations
import logging
from typing import Optional

from backend.utils.helpers import DF, downcast_numeric, is_gpu
from backend.io.data_loader import load_data, save_data

log = logging.getLogger("features.user")


def build_user_features(
    interactions_path: str,
    out_path: Optional[str] = None,
    user_col: str = "userId",
    rating_col: str = "rating",
) -> DF:
    """
    Vectorized computation of PER-USER rating aggregates only.
    Sequence / timestamp features intentionally removed.

    Args:
        interactions_path: path to interactions parquet/csv
        out_path: optional path to save the output
    Returns:
        DF of user-level rating stats
    """

    log.info("Building user *rating* features from %s (gpu=%s)", interactions_path, is_gpu())

    df = load_data(interactions_path)

    # Ensure required columns exist
    required = {user_col}
    if rating_col in df.columns:
        required.add(rating_col)

    if not required.issubset(df.columns):
        raise ValueError(f"Missing required columns: {required - set(df.columns)}")

    # Cast for performance
    df[user_col] = df[user_col].astype("int32")
    df[rating_col] = df[rating_col].astype("float32")

    # ---- USER AGGREGATIONS (rating-only) ----
    g = df.groupby(user_col)
    user_stats = g.agg({
        rating_col: ["count", "mean", "std"]
    })

    # Rename columns
    user_stats.columns = [
        "user_rating_count",
        "user_rating_mean",
        "user_rating_std",
    ]

    # Reset index for merge compatibility
    user_stats = user_stats.reset_index()

    # Downcast for memory efficiency
    user_stats = downcast_numeric(user_stats)

    # Save if requested
    if out_path:
        save_data(user_stats, out_path)
        log.info("Saved user features to %s", out_path)

    return user_stats

