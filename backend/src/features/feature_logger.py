import logging
from typing import Iterable, List

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

logger = logging.getLogger(__name__)


class FeatureLogger:
    def __init__(
        self,
        output_path: str,
        chunk_size: int = 500_000,
    ) -> None:
        self.output_path = output_path
        self.chunk_size = chunk_size
        self._writer: pq.ParquetWriter | None = None

    def write_stream(self, rows: Iterable[dict]) -> None:
        buffer: List[dict] = []

        for row in rows:
            buffer.append(row)

            if len(buffer) >= self.chunk_size:
                self.write_rows(buffer)
                buffer.clear()

        if buffer:
            self.write_rows(buffer)
        
        self.close()

    def write_rows(self, rows: List[dict]) -> None:
        """Appends a list of rows to the Parquet file."""
        if not rows:
            return
            
        df = pd.DataFrame(rows)

        df = df.astype(
            {
                "user_id": "int32",
                "item_id": "int32",
                "label": "int8",
                "num_retrievers": "int8",
            },
            errors="ignore",
        )

        table = pa.Table.from_pandas(df, preserve_index=False)

        if self._writer is None:
            self._writer = pq.ParquetWriter(
                self.output_path,
                table.schema,
                compression="snappy",
            )
        
        self._writer.write_table(table)

        logger.info("Flushed %d rows", len(rows))

    def close(self):
        if self._writer:
            self._writer.close()
            logger.info("Feature logging completed: %s", self.output_path)
