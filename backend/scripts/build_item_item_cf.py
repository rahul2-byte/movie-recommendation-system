#!/usr/bin/env python3
"""
Build Item–Item Collaborative Filtering artifacts.

Usage:
  python scripts/build_item_item_cf.py \
    --interactions data/processed/interactions.parquet \
    --models_dir models/item_item_cf
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix, save_npz

from retrieval.item_item_cf import (
    ItemItemCFBuilder,
    ItemItemCFConfig,
)

# ---------------------------------------------------------
# Logging
# ---------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("build_item_item_cf")


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------
def build_user_item_matrix(
    df: pd.DataFrame,
) -> Tuple[csr_matrix, np.ndarray]:
    """
    Build sparse user–item matrix.

    Expected columns:
      - userId
      - movieId
      - rating (rating or implicit=1)

    Returns:
        matrix: CSR user–item matrix
        item_ids: array mapping column index -> movieId
    """
    logger.info("Building user–item sparse matrix")

    user_codes, user_index = pd.factorize(df["userId"], sort=True)
    item_codes, item_index = pd.factorize(df["movieId"], sort=True)

    matrix = csr_matrix(
        (
            df["rating"].astype(np.float32).to_numpy(),
            (user_codes, item_codes),
        ),
        shape=(len(user_index), len(item_index)),
        dtype=np.float32,
    )

    logger.info(
        "Matrix shape users=%d items=%d nnz=%d",
        matrix.shape[0],
        matrix.shape[1],
        matrix.nnz,
    )

    return matrix, item_index.to_numpy()


# ---------------------------------------------------------
# CLI
# ---------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser("Build Item–Item CF")

    parser.add_argument(
        "--interactions",
        type=Path,
        required=True,
        help="Path to interactions parquet/csv",
    )
    parser.add_argument(
        "--models_dir",
        type=Path,
        required=True,
        help="Output directory for ItemCF artifacts",
    )
    parser.add_argument(
        "--top_k",
        type=int,
        default=100,
        help="Top-K neighbors per item",
    )
    parser.add_argument(
        "--implicit",
        action="store_true",
        help="Use implicit feedback weighting",
    )
    parser.add_argument(
        "--alpha",
        type=float,
        default=40.0,
        help="Implicit confidence alpha",
    )

    return parser.parse_args()


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------
def main() -> None:
    args = parse_args()

    logger.info("Loading interactions from %s", args.interactions)

    if args.interactions.suffix == ".parquet":
        df = pd.read_parquet(args.interactions)
    else:
        df = pd.read_csv(args.interactions)

    required_cols = {"userId", "movieId", "rating"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    matrix, item_ids = build_user_item_matrix(df)

    config = ItemItemCFConfig(
        top_k_per_item=args.top_k,
        use_implicit=args.implicit,
        implicit_alpha=args.alpha,
    )

    builder = ItemItemCFBuilder(config)
    similarity = builder.build(matrix)

    # -----------------------------------------------------
    # Persist artifacts
    # -----------------------------------------------------
    args.models_dir.mkdir(parents=True, exist_ok=True)

    sim_path = args.models_dir / "similarity.npz"
    items_path = args.models_dir / "item_ids.npy"
    meta_path = args.models_dir / "metadata.json"

    logger.info("Saving similarity matrix to %s", sim_path)
    save_npz(sim_path, similarity)

    logger.info("Saving item id mapping")
    np.save(items_path, item_ids)

    metadata = {
        "num_users": matrix.shape[0],
        "num_items": matrix.shape[1],
        "nnz": int(matrix.nnz),
        "top_k": args.top_k,
        "implicit": args.implicit,
        "alpha": args.alpha,
    }

    meta_path.write_text(json.dumps(metadata, indent=2))
    logger.info("Saved metadata")

    logger.info("Item–Item CF build complete")


if __name__ == "__main__":
    main()
