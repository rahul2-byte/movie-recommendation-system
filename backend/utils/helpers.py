import gc
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import numpy as np

# Try to import GPU stack libs; if not present fallback to CPU libs
try:
    import cudf as gd
    import cupy as cp
    GPU_AVAILABLE = True
except Exception:
    import pandas as gd
    import numpy as cp
    GPU_AVAILABLE = False

# For type-hint clarity
DF = Any

# Configure basic logger
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

def is_gpu() -> bool:
    """Return True if GPU libs are available (cudf/cupy)."""
    return GPU_AVAILABLE

def read_parquet(path: str) -> DF:
    """Read parquet into cudf.DataFrame if available, else pandas."""
    logger.debug("Reading parquet: %s (gpu=%s)", path, GPU_AVAILABLE)
    return gd.read_parquet(path)

def to_parquet(df: DF, path: str, compression: str = "snappy") -> None:
    """Persist DataFrame to parquet; ensures directory exists."""
    logger.debug("Writing parquet to: %s", path)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, compression=compression)

def downcast_numeric(df: DF) -> DF:
    """
    Downcast numeric columns in-place where possible to reduce memory:
    - float64 -> float32
    - int64 -> int32
    Works for cudf.DataFrame and pandas.DataFrame.
    """
    logger.debug("Downcasting numeric dtypes")
    for col in df.columns:
        try:
            col_dtype = df[col].dtype
            if str(col_dtype).startswith("float") and col_dtype.itemsize > 4:
                df[col] = df[col].astype("float32")
            if str(col_dtype).startswith("int") and col_dtype.itemsize > 4:
                df[col] = df[col].astype("int32")
        except Exception:
            continue
    return df

def set_categorical(df: DF, cols: Tuple[str, ...]) -> DF:
    """Convert provided columns to category dtype (if supported)."""
    for col in cols:
        try:
            df[col] = df[col].astype("category")
        except Exception:
            logger.debug("Failed to set categorical for col=%s", col)
    return df

def free(*objs: Any) -> None:
    """Delete references and run garbage collector to free memory."""
    for o in objs:
        try:
            del o
        except Exception:
            pass
    gc.collect()

def compute_ranks(scores: Dict[int, float]) -> Dict[int, int]:
    """
    Compute rank per item (1 = best).
    """
    if not scores:
        return {}

    items, values = zip(*scores.items())
    order = np.argsort(-np.array(values))
    ranks = np.empty_like(order)
    ranks[order] = np.arange(1, len(order) + 1)

    return {items[i]: int(ranks[i]) for i in range(len(items))}