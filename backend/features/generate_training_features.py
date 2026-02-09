# backend/features/generate_training_features.py
"""
Batch feature generator for the ranking dataset.
Standardizes logic for both Python serving and C++ offline training.
"""

import logging
import os
from pathlib import Path

import numpy as np
import pandas as pd
from common.config import config
from features.builder import FeatureBuilder

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
log = logging.getLogger(__name__)


def generate_features():
    # 1. Paths from config
    input_path = "backend/data/processed/ranking_dataset.parquet"
    output_path = "backend/data/processed/ranking_featured.parquet"
    movies_path = "backend/data/processed/movies_enriched.parquet"
    tags_path = "backend/data/processed/tags.parquet"

    if not os.path.exists(input_path):
        log.error(f"Input file not found: {input_path}")
        return

    log.info("Initializing FeatureBuilder...")
    # FeatureBuilder.from_paths builds genre/tag matrices internally for fast lookup
    fb = FeatureBuilder.from_paths(movies_path, tags_path)

    log.info(f"Loading raw dataset from {input_path}...")
    df_raw = pd.read_parquet(input_path)
    log.info(f"Processing {len(df_raw)} rows...")

    # Data Validation
    required_cols = ["query_movie_ids", "candidate_movie_id", "label"]
    for col in required_cols:
        if col not in df_raw.columns:
            raise ValueError(f"Missing required column: {col}")

    # Build features in one pass
    # The build_features method handles the heavy lifting using vectorized ops
    df_featured = fb.build_features(df_raw)

    # Final Schema Check/Enforcement
    # Ensure float32 for model training memory efficiency
    float_cols = [c for c in df_featured.columns if c.startswith("feat_")]
    for col in float_cols:
        if "count" not in col:
            df_featured[col] = df_featured[col].astype(np.float32)

    log.info(f"Saving featured dataset to {output_path}...")
    # Use Snappy compression for Parquet balance between speed and size
    df_featured.to_parquet(
        output_path, engine="pyarrow", compression="snappy", index=False
    )

    log.info("✨ Feature generation complete! ✨")


if __name__ == "__main__":
    generate_features()
