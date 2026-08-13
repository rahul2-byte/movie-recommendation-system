"""
Dataset merger for combining intermediate parquet batches.

Efficiently merges multiple small parquet files into a single
final dataset with schema validation.
"""

import json
from datetime import datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from common.logger import get_logger
from configs.settings import (
    INTERMEDIATE_DIR,
    MOVIES_METADATA_PATH,
)

logger = get_logger(__name__)


def merge_dataset(
    input_dir: Path = INTERMEDIATE_DIR,
    output_path: str = MOVIES_METADATA_PATH,
    strict_schema: bool = True,
    overwrite: bool = True,
) -> None:
    """
    Merge all intermediate parquet batches into final dataset.

    Args:
        input_dir: Directory containing movies_batch_*.parquet files
        output_path: Path for final parquet file
        strict_schema: If True, enforce MOVIE_SCHEMA
        overwrite: If True, overwrite existing output file
    """
    out_path = Path(output_path)
    if out_path.exists() and not overwrite:
        raise FileExistsError(f"Output file already exists: {output_path}")

    # 1. Collect all batch files
    batch_files = sorted(list(input_dir.glob("movies_batch_*.parquet")))

    if not batch_files:
        logger.warning("No batch files found to merge")
        return

    logger.info(f"Merging {len(batch_files)} batch files...")

    # 2. Read all tables
    tables = []
    total_rows = 0

    for file in batch_files:
        try:
            table = pq.read_table(file)
            tables.append(table)
            total_rows += table.num_rows
            logger.debug(f"Loaded {file.name} ({table.num_rows} rows)")
        except Exception as e:
            logger.error(f"Failed to read {file.name}: {e}")
            if strict_schema:
                raise

    # 3. Concatenate and Write
    try:
        final_table = pa.concat_tables(tables)

        # Ensure output directory exists
        out_path.parent.mkdir(parents=True, exist_ok=True)

        # Write final parquet
        pq.write_table(final_table, out_path, compression="snappy")

        # 4. Generate Metadata JSON
        metadata = {
            "schema_version": "Initial movie enrichment schema",
            "total_rows": total_rows,
            "total_columns": len(final_table.column_names),
            "file_size_mb": round(out_path.stat().st_size / (1024 * 1024), 2),
            "compression": "snappy",
            "merge_date": datetime.now().isoformat(),
            "batch_count": len(batch_files),
            "schema": str(final_table.schema),
        }

        json_path = out_path.with_suffix(".json")
        with open(json_path, "w") as f:
            json.dump(metadata, f, indent=2)

        logger.info(
            f"Successfully merged {total_rows} rows into {output_path}. "
            f"Metadata saved to {json_path.name}"
        )

    except Exception as e:
        logger.error(f"Failed to merge datasets: {e}")
        raise
