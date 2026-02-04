"""
Parquet file writer for intermediate and final movie data.

Provides efficient streaming writes to minimize memory usage.
"""

from pathlib import Path
from typing import List
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from common.models.movie import MovieData, MOVIE_SCHEMA
from configs.settings import INTERMEDIATE_DIR
from common.logger import get_logger

logger = get_logger(__name__)


class ParquetWriter:
    """
    Writer for streaming movie data to parquet files.
    
    Buffers data in memory and writes when buffer reaches threshold
    to balance memory usage and write efficiency.
    """
    
    def __init__(
        self,
        output_dir: Path = INTERMEDIATE_DIR,
        buffer_size: int = 100,
    ):
        """
        Initialize parquet writer.
        
        Args:
            output_dir: Directory for intermediate parquet files
            buffer_size: Number of records to buffer before writing
        """
        self.output_dir = output_dir
        self.buffer_size = buffer_size
        self.buffer: List[MovieData] = []
        self.file_counter = 0
        self.total_written = 0
    
    def add(self, movie: MovieData) -> None:
        """
        Add a movie to the write buffer.
        
        Automatically flushes when buffer is full.
        
        Args:
            movie: MovieData object to add
        """
        self.buffer.append(movie)
        
        if len(self.buffer) >= self.buffer_size:
            self.flush()
    
    def flush(self) -> None:
        """
        Write buffered data to parquet file.
        
        Creates a new intermediate file with sequential numbering.
        """
        if not self.buffer:
            return
        
        try:
            # Convert MovieData objects to dictionaries
            records = [movie.to_dict() for movie in self.buffer]
            
            # Create DataFrame and convert to PyArrow Table
            df = pd.DataFrame(records)
            table = pa.Table.from_pandas(df, schema=MOVIE_SCHEMA)
            
            # Generate output filename
            output_path = (
                self.output_dir / f"movies_batch_{self.file_counter:05d}.parquet"
            )
            
            # Write parquet file
            pq.write_table(table, output_path, compression="snappy")
            
            logger.info(
                f"Wrote batch {self.file_counter}: "
                f"{len(self.buffer)} records to {output_path.name}"
            )
            
            self.total_written += len(self.buffer)
            self.buffer.clear()
            self.file_counter += 1
            
        except Exception as e:
            logger.error(f"Failed to write parquet batch: {e}")
            raise
    
    def close(self) -> int:
        """
        Flush remaining buffer and finalize writing.
        
        Returns:
            Total number of records written
        """
        self.flush()
        logger.info(f"Parquet writer closed: {self.total_written} total records written")
        return self.total_written


def write_parquet_batch(
    movies: List[MovieData],
    output_path: Path,
) -> None:
    """
    Write a batch of movies to a single parquet file.
    
    Utility function for one-off writes.
    
    Args:
        movies: List of MovieData objects
        output_path: Path to output parquet file
    """
    if not movies:
        logger.warning("No movies to write")
        return
    
    records = [movie.to_dict() for movie in movies]
    df = pd.DataFrame(records)
    table = pa.Table.from_pandas(df, schema=MOVIE_SCHEMA)
    
    pq.write_table(table, output_path, compression="snappy")
    logger.info(f"Wrote {len(movies)} records to {output_path}")