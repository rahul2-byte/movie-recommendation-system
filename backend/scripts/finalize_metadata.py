import pandas as pd
import numpy as np
from pathlib import Path
import logging
import sys
import os

# Add backend to path to allow imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

from common.config import config

def clean_list(x):
    if not isinstance(x, (list, np.ndarray)):
        return []
    # Lowercase, strip, and deduplicate
    cleaned = sorted(list(set(str(i).lower().strip() for i in x if i)))
    return cleaned

def main():
    # Resolve path relative to project root (up one level from backend/)
    project_root = Path(__file__).resolve().parent.parent.parent
    path = project_root / config.system.movies_metadata_path
    
    if not path.exists():
        log.error(f"Metadata not found at {path}!")
        return

    log.info(f"Standardizing metadata in {path}...")
    df = pd.read_parquet(path)

    # 1. Lowercase simple string columns
    str_cols = ['title', 'overview', 'director', 'language', 'country', 'collection_name']
    for col in str_cols:
        if col in df.columns:
            df[col] = df[col].str.lower().str.strip()

    # 2. Lowercase and deduplicate list columns
    list_cols = ['genres', 'keywords', 'top_cast']
    for col in list_cols:
        if col in df.columns:
            df[col] = df[col].apply(clean_list)

    # 3. Deduplicate rows by movie_id if any
    original_len = len(df)
    df = df.drop_duplicates(subset=['movie_id'])
    if len(df) < original_len:
        log.info(f"Removed {original_len - len(df)} duplicate movie IDs.")

    df.to_parquet(path, index=False)
    log.info("Metadata standardization complete.")

if __name__ == "__main__":
    main()
