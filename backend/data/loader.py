
import json
from pathlib import Path
import pandas as pd
from typing import Any, Dict, Optional, Tuple
import pyarrow as pa
import pyarrow.parquet as pq

def read_csv(path: str, usecols: Optional[Tuple[str, ...]] = None, dtype: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
    """Read CSV using pandas with minimal memory footprint."""
    return pd.read_csv(path, usecols=usecols, dtype=dtype)

def to_parquet(df: pd.DataFrame, path: str):
    """Save DataFrame to Parquet format."""
    table = pa.Table.from_pandas(df)
    pq.write_table(table, path)

def load_data(path: str) -> pd.DataFrame:
    """Load data from CSV or Parquet file."""
    if path.endswith(".csv"):
        return read_csv(path)
    elif path.endswith(".parquet"):
        return pd.read_parquet(path)
    else:
        raise ValueError(f"Unsupported file format: {path}")

def save_data(df: pd.DataFrame, path: str):
    """Save DataFrame to CSV or Parquet file."""
    if path.endswith(".csv"):
        df.to_csv(path, index=False)
    elif path.endswith(".parquet"):
        to_parquet(df, path)
    else:
        raise ValueError(f"Unsupported file format: {path}")


def load_movies_metadata(data_dir: str = "data/processed") -> pd.DataFrame:
    """Loads enriched movies metadata."""
    file_path = Path(__file__).resolve().parents[1] / data_dir / "movies_enriched_metadata.json"
    with open(file_path, "r") as f:
        data = json.load(f)
    return pd.DataFrame.from_dict(data)

def load_movielens_movies(data_dir: str = "data/raw") -> pd.DataFrame:
    """Loads movielens movies data."""
    path = Path(__file__).resolve().parents[1] / data_dir / "movies.csv"
    return read_csv(path)

def load_movielens_ratings(data_dir: str = "data/raw") -> pd.DataFrame:
    """Loads movielens ratings data."""
    path = Path(__file__).resolve().parents[1] / data_dir / "ratings.csv"
    return read_csv(path)

def load_movielens_links(data_dir: str = "data/raw") -> pd.DataFrame:
    """Loads movielens links data."""
    path = Path(__file__).resolve().parents[1] / data_dir / "links.csv"
    return read_csv(path)

def load_processed_ratings(data_dir: str = "data/processed") -> pd.DataFrame:
    """Loads processed ratings parquet file."""
    path = Path(__file__).resolve().parents[1] / data_dir / "ratings.parquet"
    return pd.read_parquet(path)
