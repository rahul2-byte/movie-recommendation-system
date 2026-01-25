#!/usr/bin/env python3
"""
Orchestrates content-based TF-IDF embedding creation.

All embedding logic lives in:
    src/retrieval/content_based/

This script only:
- loads input data
- calls the encoder
- triggers artifact persistence
"""


import argparse
import logging
from pathlib import Path

import polars as pl

from src.retrieval.content_based_tfidf_encoder import TfidfConfig, TfidfEncoder

# ---------------------------------------------------------
# Logging
# ---------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
LOGGER = logging.getLogger("build_content_based_embeddings")


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------
def main(args: argparse.Namespace) -> None:
    LOGGER.info("Loading input data")

    items_df = pl.read_csv(args.items)
    tags_df = pl.read_csv(args.tags)

    config = TfidfConfig(
        artifact_dir=Path(args.out_dir),
    )

    encoder = TfidfEncoder(config)

    LOGGER.info("Building TF-IDF embeddings via content_based module")

    X, item_id_map = encoder.fit_transform(
        items_df=items_df,
        tags_df=tags_df,
    )

    encoder.save_artifacts(
        embeddings=X,
        item_id_map=item_id_map
    )

    LOGGER.info("Content-based embeddings build complete")


# ---------------------------------------------------------
# CLI
# ---------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build content-based TF-IDF embeddings"
    )

    parser.add_argument(
        "--items",
        type=str,
        required=True,
        help="Path to items.csv (movieId, title)",
    )

    parser.add_argument(
        "--tags",
        type=str,
        required=True,
        help="Path to tags.csv (movieId, tag)",
    )

    parser.add_argument(
        "--out-dir",
        type=str,
        default="models/content_based",
        help="Directory to write embedding artifacts",
    )

    return parser.parse_args()


if __name__ == "__main__":
    main(parse_args())
