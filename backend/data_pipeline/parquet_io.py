"""Atomic Parquet output shared by offline dataset pipelines."""

from pathlib import Path
from typing import Any


def write_parquet(
    frame: Any, path: Path, *, compression: str, compression_level: int
) -> None:
    """Atomically write one compressed Parquet file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    frame.to_parquet(
        temporary,
        index=False,
        compression=compression,
        compression_level=compression_level,
    )
    temporary.replace(path)
