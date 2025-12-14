# features/utils.py
"""
Utilities: GPU detection, read/write wrappers, dtype downcasting, logging setup.

Design goals:
- Use cudf/cupy when available; fallback to pandas/numpy for portability.
- Minimal overhead wrappers with consistent API across GPU/CPU.
"""

from __future__ import annotations

import gc
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# Try to import GPU stack libs; if not present fallback to CPU libs
try:
    import cudf as gd  # type: ignore
    import cupy as cp  # type: ignore
    GPU_AVAILABLE = True
except Exception:
    import pandas as gd  # type: ignore
    import numpy as cp  # type: ignore  # alias to minimize code diffs
    GPU_AVAILABLE = False  # type: ignore

# For type-hint clarity
DF = Any

# Configure basic logger
logger = logging.getLogger("features")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(os.environ.get("FEATURES_LOG_LEVEL", "INFO"))

def is_gpu() -> bool:
    """Return True if GPU libs are available (cudf/cupy)."""
    return GPU_AVAILABLE

def read_parquet(path: str) -> DF:
    """Read parquet into cudf.DataFrame if available, else pandas."""
    logger.debug("Reading parquet: %s (gpu=%s)", path, GPU_AVAILABLE)
    if is_gpu():
        return gd.read_parquet(path)
    else:
        return gd.read_parquet(path)

def read_csv(path: str, usecols: Optional[Tuple[str, ...]] = None, dtype: Optional[Dict[str, Any]] = None) -> DF:
    """Read CSV using cudf/pandas with minimal memory footprint."""
    logger.debug("Reading csv: %s", path)
    if is_gpu():
        # cudf.read_csv supports dtype param
        return gd.read_csv(path, usecols=list(usecols) if usecols else None, dtype=dtype)
    else:
        return gd.read_csv(path, usecols=usecols, dtype=dtype)

def to_parquet(df: DF, path: str, compression: str = "snappy") -> None:
    """Persist DataFrame to parquet; ensures directory exists."""
    logger.debug("Writing parquet to: %s", path)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    if is_gpu():
        df.to_parquet(path, compression=compression)
    else:
        df.to_parquet(path, compression=compression)

def downcast_numeric(df: DF) -> DF:
    """
    Downcast numeric columns in-place where possible to reduce memory:
    - float64 -> float32
    - int64 -> int32
    Works for cudf.DataFrame and pandas.DataFrame.
    """
    logger.debug("Downcasting numeric dtypes")
    # cudf/pandas have similar dtypes API
    for col in df.columns:
        try:
            col_dtype = df[col].dtype
            # float downcast
            if str(col_dtype).startswith("float") and col_dtype.itemsize > 4:
                df[col] = df[col].astype("float32")
            # int downcast
            if str(col_dtype).startswith("int") and col_dtype.itemsize > 4:
                df[col] = df[col].astype("int32")
        except Exception:
            # ignore columns that fail casting (e.g., lists)
            continue
    return df

def set_categorical(df: DF, cols: Tuple[str, ...]) -> DF:
    """Convert provided columns to category dtype (if supported)."""
    for col in cols:
        try:
            if is_gpu():
                df[col] = df[col].astype("category")
            else:
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
