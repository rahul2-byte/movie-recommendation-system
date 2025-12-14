"""
Correct split script for your pipeline:
1. Load ratings (interactions)
2. Load engineered user features
3. Load engineered item features
4. Merge everything into ONE big engineered interaction table
5. Temporal split this table
"""

from __future__ import annotations
import argparse
import logging
from pathlib import Path
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
LOGGER = logging.getLogger(__name__)


def temporal_user_split(df, val_ratio, test_ratio):
    df = df.sort_values(["userId", "timestamp"])
    df["_rank"] = df.groupby("userId").cumcount()
    df["_cnt"] = df.groupby("userId")["movieId"].transform("count")

    test_cut = (1 - test_ratio) * df["_cnt"]
    val_cut = (1 - test_ratio - val_ratio) * df["_cnt"]

    train = df[df["_rank"] < val_cut]
    val = df[(df["_rank"] >= val_cut) & (df["_rank"] < test_cut)]
    test = df[df["_rank"] >= test_cut]

    for d in (train, val, test):
        d.drop(columns=["_rank", "_cnt"], inplace=True)

    return train, val, test


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--ratings", required=True)
    parser.add_argument("--users", required=True)
    parser.add_argument("--items", required=True)
    parser.add_argument("--out_dir", default="data/processed/splits")
    parser.add_argument("--val_ratio", type=float, default=0.1)
    parser.add_argument("--test_ratio", type=float, default=0.1)
    args = parser.parse_args()

    # Load data
    ratings = (
        pd.read_parquet(args.ratings)
        if args.ratings.endswith(".parquet")
        else pd.read_csv(args.ratings)
    )

    users = pd.read_parquet(args.users)
    items = pd.read_parquet(args.items)

    LOGGER.info("Merging user and item features into ratings...")

    # Merge user features
    merged = ratings.merge(users, on="userId", how="left")

    # Merge item features
    merged = merged.merge(items, on="movieId", how="left")

    LOGGER.info("Final engineered dataset shape: %s", merged.shape)

    # SPLIT THIS ENGINEERED DATASET
    train, val, test = temporal_user_split(
        merged,
        args.val_ratio,
        args.test_ratio,
    )

    # Save results
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    train.to_parquet(out_dir / "train.parquet", index=False)
    val.to_parquet(out_dir / "val.parquet", index=False)
    test.to_parquet(out_dir / "test.parquet", index=False)

    LOGGER.info("Train=%d | Val=%d | Test=%d", len(train), len(val), len(test))
    LOGGER.info("Split complete.")


if __name__ == "__main__":
    main()
