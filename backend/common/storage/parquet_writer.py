"""
Buffered parquet writer for enrichment batches.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
from configs.settings import INTERMEDIATE_DIR

from common.logger import get_logger
from common.models.movie import MOVIE_SCHEMA

logger = get_logger(__name__)


class ParquetWriter:
    def __init__(self, output_dir: Path = INTERMEDIATE_DIR, batch_size: int = 1000):
        self.output_dir = output_dir
        self.batch_size = batch_size
        self.buffer: list[dict[str, Any]] = []
        self.file_index = 0
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _to_record(self, movie_data: Any) -> dict[str, Any]:
        if movie_data is None:
            return {}
        if is_dataclass(movie_data):
            return asdict(movie_data)
        if isinstance(movie_data, dict):
            return movie_data
        if hasattr(movie_data, "to_dict"):
            return movie_data.to_dict()
        raise TypeError(f"Unsupported movie record type: {type(movie_data)}")

    def add(self, movie_data: Any) -> None:
        record = self._to_record(movie_data)
        if not record:
            return
        self.buffer.append(record)
        if len(self.buffer) >= self.batch_size:
            self.flush()

    def flush(self) -> None:
        if not self.buffer:
            return

        table = pa.Table.from_pylist(self.buffer, schema=MOVIE_SCHEMA)
        output_path = self.output_dir / f"movies_batch_{self.file_index:06d}.parquet"
        pq.write_table(table, output_path, compression="snappy")
        logger.info(f"Wrote batch file: {output_path}")
        self.file_index += 1
        self.buffer.clear()

    def close(self) -> None:
        self.flush()
