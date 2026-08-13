"""Storage adapters for checkpoint and parquet pipeline outputs."""

from .checkpoint import CheckpointData, CheckpointManager
from .parquet_writer import ParquetWriter

__all__ = [
    "CheckpointManager",
    "CheckpointData",
    "ParquetWriter",
]
"""Checkpoint and Parquet persistence used by ingestion jobs."""
"""Storage adapters used while materializing offline pipeline outputs."""
