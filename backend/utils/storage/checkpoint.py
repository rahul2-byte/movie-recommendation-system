"""
Checkpoint management for resumable pipeline execution.

Provides atomic checkpoint persistence for tracking progress
at the movie level (not just batch level).
"""

import json
from pathlib import Path
from typing import Dict, Set, Optional
from dataclasses import dataclass, asdict
import tempfile
import shutil

from utils.config.settings import CHECKPOINT_FILE, FAILED_MOVIES_FILE
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class CheckpointData:
    """
    Checkpoint data structure.
    
    Attributes:
        last_processed_movie_id: Last successfully processed movie ID
        processed_count: Total number of movies processed
        failed_movie_ids: Set of movie IDs that failed
        schema_version: Schema version used for this run
    """
    last_processed_movie_id: Optional[int] = None
    processed_count: int = 0
    failed_movie_ids: Set[int] = None
    schema_version: str = "1.0.0"
    
    def __post_init__(self):
        """Initialize mutable default."""
        if self.failed_movie_ids is None:
            self.failed_movie_ids = set()


class CheckpointManager:
    """
    Manager for checkpoint persistence and recovery.
    
    Provides atomic writes to prevent corruption during crashes.
    """
    
    def __init__(
        self,
        checkpoint_path: Path = CHECKPOINT_FILE,
        failed_movies_path: Path = FAILED_MOVIES_FILE,
    ):
        """
        Initialize checkpoint manager.
        
        Args:
            checkpoint_path: Path to checkpoint JSON file
            failed_movies_path: Path to failed movies JSON file
        """
        self.checkpoint_path = checkpoint_path
        self.failed_movies_path = failed_movies_path
    
    def load(self) -> CheckpointData:
        """
        Load checkpoint from disk.
        
        Returns:
            CheckpointData object, or fresh instance if no checkpoint exists
        """
        if not self.checkpoint_path.exists():
            logger.info("No checkpoint found, starting fresh")
            return CheckpointData()
        
        try:
            with open(self.checkpoint_path, "r") as f:
                data = json.load(f)
            
            # Convert failed_movie_ids list back to set
            failed_ids = set(data.get("failed_movie_ids", []))
            
            checkpoint = CheckpointData(
                last_processed_movie_id=data.get("last_processed_movie_id"),
                processed_count=data.get("processed_count", 0),
                failed_movie_ids=failed_ids,
                schema_version=data.get("schema_version", "1.0.0"),
            )
            
            logger.info(
                f"Loaded checkpoint: {checkpoint.processed_count} movies processed, "
                f"{len(checkpoint.failed_movie_ids)} failed"
            )
            return checkpoint
            
        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            logger.warning("Starting with fresh checkpoint")
            return CheckpointData()
    
    def save(self, checkpoint: CheckpointData) -> None:
        """
        Atomically save checkpoint to disk.
        
        Uses atomic write (write to temp file, then rename) to prevent
        corruption if process crashes during write.
        
        Args:
            checkpoint: CheckpointData to persist
        """
        try:
            # Convert set to list for JSON serialization
            data = asdict(checkpoint)
            data["failed_movie_ids"] = list(checkpoint.failed_movie_ids)
            
            # Atomic write: write to temp file, then rename
            temp_fd, temp_path = tempfile.mkstemp(
                dir=self.checkpoint_path.parent,
                prefix=".checkpoint_",
                suffix=".tmp",
            )
            
            try:
                with open(temp_fd, "w") as f:
                    json.dump(data, f, indent=2)
                
                # Atomic rename
                shutil.move(temp_path, self.checkpoint_path)
                
            except Exception:
                # Clean up temp file on error
                Path(temp_path).unlink(missing_ok=True)
                raise
            
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
            raise
    
    def save_failed_movies(self, failed_ids: Set[int]) -> None:
        """
        Save detailed failed movies list.
        
        Args:
            failed_ids: Set of movie IDs that failed processing
        """
        if not failed_ids:
            return
        
        try:
            data = {
                "failed_count": len(failed_ids),
                "movie_ids": sorted(failed_ids),
            }
            
            with open(self.failed_movies_path, "w") as f:
                json.dump(data, f, indent=2)
            
            logger.info(
                f"Saved {len(failed_ids)} failed movie IDs to {self.failed_movies_path}"
            )
            
        except Exception as e:
            logger.error(f"Failed to save failed movies list: {e}")
    
    def clear(self) -> None:
        """Clear checkpoint and failed movies files."""
        self.checkpoint_path.unlink(missing_ok=True)
        self.failed_movies_path.unlink(missing_ok=True)
        logger.info("Checkpoint cleared")
    
    def should_process_movie(
        self,
        movie_id: int,
        checkpoint: CheckpointData,
    ) -> bool:
        """
        Determine if a movie should be processed based on checkpoint.
        
        Args:
            movie_id: Movie ID to check
            checkpoint: Current checkpoint data
            
        Returns:
            True if movie should be processed, False if already done
        """
        # If no checkpoint, process all movies
        if checkpoint.last_processed_movie_id is None:
            return True
        
        # Process if movie_id > last processed
        return movie_id > checkpoint.last_processed_movie_id