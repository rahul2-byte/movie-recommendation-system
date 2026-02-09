import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from common.config import config
from common.logger import get_logger
from common.model_loader import ensure_local_path

log = get_logger(__name__)


def read_csv(
    path: str,
    usecols: Optional[Tuple[str, ...]] = None,
    dtype: Optional[Dict[str, Any]] = None,
) -> pd.DataFrame:
    """Read CSV using pandas with minimal memory footprint."""
    effective_path = ensure_local_path(path)
    return pd.read_csv(effective_path, usecols=usecols, dtype=dtype)


def to_parquet(df: pd.DataFrame, path: str):
    """Save DataFrame to Parquet format."""
    table = pa.Table.from_pandas(df)
    pq.write_table(table, path)


def load_data(path: str) -> pd.DataFrame:
    """Load data from CSV or Parquet file."""
    effective_path = ensure_local_path(path)
    if str(effective_path).endswith(".csv"):
        return read_csv(effective_path)
    elif str(effective_path).endswith(".parquet"):
        return pd.read_parquet(effective_path)
    else:
        raise ValueError(f"Unsupported file format: {path}")


def load_movies_metadata() -> pd.DataFrame:
    """Loads enriched movies metadata from parquet via config."""
    path = config.system.movies_metadata_path
    log.info(f"Loading movies metadata from {path}")
    return load_data(path)


def load_movielens_movies() -> pd.DataFrame:
    """Loads movielens movies data via config."""
    # Assuming we add these to system.yml or use a default relative to data_root
    path = f"{config.system.data_root}/raw/movies.csv"
    return read_csv(path)


def load_movielens_ratings() -> pd.DataFrame:
    """Loads movielens ratings data via config."""
    path = config.system.ratings_path
    if path.endswith(".parquet"):
        return pd.read_parquet(ensure_local_path(path))
    return read_csv(path)


def load_movielens_links() -> pd.DataFrame:
    """Loads movielens links data via config."""
    path = f"{config.system.data_root}/raw/links.csv"
    return read_csv(path)


def load_processed_ratings() -> pd.DataFrame:
    """Loads processed ratings parquet file via config."""
    path = config.system.ratings_path
    return pd.read_parquet(ensure_local_path(path))

