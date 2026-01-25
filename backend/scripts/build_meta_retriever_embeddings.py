#!/usr/bin/env python3
"""
Orchestrates META retriever embedding creation.

This script:
- Loads movies, tags, and movie metadata
- Joins movie core data with metadata
- Builds content-based embeddings (128 dim)
- Saves meta-retriever embeddings for downstream ANN / ranking

All embedding logic lives in:
    src/retrieval/
"""

import argparse
import logging
from pathlib import Path

import pandas as pd

from src.retrieval.metadata_item_retriever import MetadataItemRetriever

# ---------------------------------------------------------
# Logging
# ---------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
LOGGER = logging.getLogger("build_meta_retriever_embeddings")


# ---------------------------------------------------------
# Data Loading + Join
# ---------------------------------------------------------
def load_and_prepare_items(
    movies_path: str,
    metadata_path: str,
) -> pd.DataFrame:
    """
    Load movies + metadata and join them into a single dataframe.

    Expected:
    - movies: movieId, title, genres
    - metadata: movieId, overview, keywords, cast, crew, etc.
    """

    LOGGER.info("Loading movies data: %s", movies_path)
    movies_df = pd.read_parquet(movies_path)

    LOGGER.info("Loading metadata parquet: %s", metadata_path)
    metadata_df = pd.read_parquet(metadata_path)

    metadata_df = metadata_df.drop(
        columns=["title", "genres"],
        errors="ignore"
    )

    LOGGER.info("Joining movies with metadata")
    items_df = movies_df.join(
        metadata_df.set_index("movie_id"),
        on="movieId",    # metadata_df column
        how="right",
    )

    LOGGER.info("Final joined items count: %d", items_df.size)
    return items_df


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------
def main(args: argparse.Namespace) -> None:
    LOGGER.info("Starting meta retriever embedding build")

    # -----------------------------------------------------
    # Load & prepare data
    # -----------------------------------------------------
    items_df = load_and_prepare_items(
        movies_path=args.items,
        metadata_path=args.metadata,
    )

    LOGGER.info("Loading tags data: %s", args.tags)
    tags_df = pd.read_parquet(args.tags)

    # -----------------------------------------------------
    # Encoder configuration
    # -----------------------------------------------------
    retriever = MetadataItemRetriever(
        model_name = "sentence-transformers/all-MiniLM-L6-v2",
        embedding_dim = 384
        )

    # -----------------------------------------------------
    # Build embeddings
    # -----------------------------------------------------
    LOGGER.info("Building meta retriever embeddings")

    embeddings, item_id_map = retriever.build_index(items_df)

    # -----------------------------------------------------
    # Save artifacts
    # -----------------------------------------------------
    retriever.save(
        path=Path(args.out_dir), 
        embeddings=embeddings,
        item_id_map=item_id_map)

    LOGGER.info("Meta retriever embeddings build compdete")
    LOGGER.info("Artifacts written to: %s", args.out_dir)


# ---------------------------------------------------------
# CLI
# ---------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build meta retriever embeddings"
    )

    parser.add_argument(
        "--items",
        type=str,
        required=True,
        help="Path to movies.parquet (movieId, title, genres)",
    )

    parser.add_argument(
        "--metadata",
        type=str,
        required=True,
        help="Path to movie metadata parquet (movieId, overview, keywords, etc.)",
    )

    parser.add_argument(
        "--tags",
        type=str,
        required=True,
        help="Path to tags.parquet (movieId, tag)",
    )

    parser.add_argument(
        "--out-dir",
        type=str,
        default="models/meta_retriever",
        help="Directory to write meta embedding artifacts",
    )

    return parser.parse_args()


if __name__ == "__main__":
    main(parse_args())
