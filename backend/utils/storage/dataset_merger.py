"""
Dataset merger for combining intermediate parquet files.

Merges batch files into a single parquet file with schema validation.
"""

import json
from pathlib import Path
from typing import List, Optional
import pyarrow as pa
import pyarrow.parquet as pq

from utils.models.movie import MOVIE_SCHEMA, load_schema_version
from utils.config.settings import (
    INTERMEDIATE_DIR,
    PROCESSED_DIR,
    OUTPUT_DATASET_NAME,
)
from utils.logger import get_logger

logger = get_logger(__name__)


class DatasetMerger:
    """
    Merges intermediate parquet files into a single final parquet file.
    
    Handles schema validation and metadata persistence.
    """
    
    def __init__(
        self,
        input_dir: Path = INTERMEDIATE_DIR,
        output_dir: Path = PROCESSED_DIR,
        dataset_name: str = OUTPUT_DATASET_NAME,
    ):
        """
        Initialize dataset merger.
        
        Args:
            input_dir: Directory containing intermediate parquet files
            output_dir: Directory for final dataset
            dataset_name: Name of output parquet file (without .parquet extension)
        """
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.dataset_name = dataset_name
        self.output_file = output_dir / f"{dataset_name}.parquet"
    
    def find_batch_files(self, pattern: str = "movies_batch_*.parquet") -> List[Path]:
        """
        Find all intermediate batch parquet files.
        
        Args:
            pattern: Glob pattern for batch files
            
        Returns:
            Sorted list of batch file paths
        """
        batch_files = sorted(self.input_dir.glob(pattern))
        logger.info(f"Found {len(batch_files)} batch files")
        return batch_files
    
    def validate_and_load_table(
        self,
        file_path: Path,
        strict: bool = True,
    ) -> Optional[pa.Table]:
        """
        Load and validate a single parquet file.
        
        Args:
            file_path: Path to parquet file
            strict: If True, fail on schema mismatch; if False, attempt cast
            
        Returns:
            PyArrow Table or None if validation fails
        """
        try:
            table = pq.read_table(file_path)
            
            # Validate schema
            if not table.schema.equals(MOVIE_SCHEMA):
                if strict:
                    logger.error(
                        f"Schema mismatch in {file_path.name}\n"
                        f"Expected: {MOVIE_SCHEMA}\n"
                        f"Got: {table.schema}"
                    )
                    return None
                else:
                    logger.warning(
                        f"Schema mismatch in {file_path.name}, attempting cast"
                    )
                    table = table.cast(MOVIE_SCHEMA)
            
            return table
            
        except Exception as e:
            logger.error(f"Failed to load {file_path.name}: {e}")
            return None
    
    def merge(
        self,
        strict_schema: bool = True,
        overwrite: bool = True,
        compression: str = "snappy",
    ) -> None:
        """
        Merge all intermediate parquet files into a single final file.
        
        Args:
            strict_schema: If True, fail on schema mismatches
            overwrite: If True, overwrite existing output file
            compression: Compression codec (snappy, gzip, zstd, none)
            
        Raises:
            RuntimeError: If no valid batch files found
            FileExistsError: If output file exists and overwrite=False
        """
        logger.info("=" * 60)
        logger.info("Starting dataset merge")
        logger.info("=" * 60)
        
        # Check if output file exists
        if self.output_file.exists() and not overwrite:
            raise FileExistsError(
                f"Output file already exists: {self.output_file}\n"
                f"Use overwrite=True or --no-overwrite flag to skip"
            )
        
        # Find batch files
        batch_files = self.find_batch_files()
        if not batch_files:
            raise RuntimeError(
                f"No batch parquet files found in {self.input_dir}"
            )
        
        # Load and validate tables
        valid_tables = []
        failed_files = []
        
        for file_path in batch_files:
            table = self.validate_and_load_table(file_path, strict=strict_schema)
            if table is not None:
                valid_tables.append(table)
            else:
                failed_files.append(file_path.name)
        
        if not valid_tables:
            raise RuntimeError("No valid parquet batches after validation")
        
        logger.info(
            f"Loaded {len(valid_tables)} valid tables "
            f"({len(failed_files)} failed validation)"
        )
        
        # Concatenate all tables
        full_table = pa.concat_tables(valid_tables)
        logger.info(f"Total rows in merged dataset: {full_table.num_rows:,}")
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Write single parquet file
        logger.info(f"Writing merged parquet file to {self.output_file}")
        
        pq.write_table(
            full_table,
            self.output_file,
            compression=compression,
            use_dictionary=True,
            write_statistics=True,
        )
        
        # Get file size
        file_size_mb = self.output_file.stat().st_size / (1024 * 1024)
        
        # Save metadata
        self._save_metadata(full_table, failed_files, file_size_mb, compression)
        
        logger.info("=" * 60)
        logger.info("Dataset merge completed successfully")
        logger.info(f"Output file: {self.output_file}")
        logger.info(f"File size: {file_size_mb:.2f} MB")
        logger.info(f"Total rows: {full_table.num_rows:,}")
        logger.info(f"Failed files: {len(failed_files)}")
        logger.info("=" * 60)
    
    def _save_metadata(
        self,
        table: pa.Table,
        failed_files: List[str],
        file_size_mb: float,
        compression: str,
    ) -> None:
        """
        Save dataset metadata to JSON file.
        
        Args:
            table: Final merged table
            failed_files: List of files that failed validation
            file_size_mb: Size of output file in MB
            compression: Compression codec used
        """
        schema_version = load_schema_version()
        
        metadata = {
            "schema_version": schema_version.get("description", "1.0.0"),
            "total_rows": table.num_rows,
            "total_columns": len(table.schema),
            "file_size_mb": round(file_size_mb, 2),
            "compression": compression,
            "failed_files": failed_files,
            "output_file": str(self.output_file),
            "schema": MOVIE_SCHEMA.to_string(),
        }
        
        metadata_path = self.output_dir / f"{self.dataset_name}_metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Saved metadata to {metadata_path}")


def merge_dataset(
    strict_schema: bool = True,
    overwrite: bool = True,
    compression: str = "snappy",
) -> None:
    """
    Convenience function to merge dataset with default settings.
    
    Args:
        strict_schema: If True, fail on schema mismatches
        overwrite: If True, overwrite existing dataset
        compression: Compression codec (snappy, gzip, zstd, none)
    """
    merger = DatasetMerger()
    merger.merge(
        strict_schema=strict_schema,
        overwrite=overwrite,
        compression=compression,
    )