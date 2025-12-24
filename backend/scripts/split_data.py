"""
Temporal interaction split (PRODUCTION SAFE)

Design principles:
- Split ONLY interaction data
- No feature joins
- O(N) memory
- Works at 25M+ scale
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
LOGGER = logging.getLogger(__name__)


def temporal_user_split(
    df: pd.DataFrame,
    val_ratio: float,
    test_ratio: float,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Per-user temporal split.

    Guarantees:
    - No leakage
    - User order preserved
    - Constant memory overhead
    """
    df = df.sort_values(["userId", "timestamp"], kind="mergesort")

    # Per-user rank
    df["_rank"] = df.groupby("userId", sort=False).cumcount()
    df["_cnt"] = df.groupby("userId", sort=False)["movieId"].transform("count")

    val_cut = (1.0 - val_ratio - test_ratio) * df["_cnt"]
    test_cut = (1.0 - test_ratio) * df["_cnt"]

    train = df[df["_rank"] < val_cut]
    val = df[(df["_rank"] >= val_cut) & (df["_rank"] < test_cut)]
    test = df[df["_rank"] >= test_cut]

    # Drop temp columns safely
    train = train.drop(columns=["_rank", "_cnt"])
    val = val.drop(columns=["_rank", "_cnt"])
    test = test.drop(columns=["_rank", "_cnt"])

    return train, val, test


def main() -> None:
    parser = argparse.ArgumentParser("Temporal split for recommender systems")
    parser.add_argument("--ratings", required=True)
    parser.add_argument("--out_dir", default="data/processed/splits")
    parser.add_argument("--val_ratio", type=float, default=0.1)
    parser.add_argument("--test_ratio", type=float, default=0.1)

    args = parser.parse_args()

    LOGGER.info("Loading interactions...")
    ratings = pd.read_csv(args.ratings)

    LOGGER.info("Splitting interactions temporally...")
    train, val, test = temporal_user_split(
        ratings,
        args.val_ratio,
        args.test_ratio,
    )

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    train.to_parquet(out_dir / "train.parquet", index=False)
    val.to_parquet(out_dir / "val.parquet", index=False)
    test.to_parquet(out_dir / "test.parquet", index=False)

    LOGGER.info(
        "Split done | train=%d val=%d test=%d",
        len(train),
        len(val),
        len(test),
    )


if __name__ == "__main__":
    main()
