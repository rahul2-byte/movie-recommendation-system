"""
Movie enrichment service orchestrating API calls and data extraction.

Main service coordinating TMDB/IMDb clients, field extraction,
and result persistence.
"""

import asyncio

import pandas as pd
from configs.settings import (
    CHECKPOINT_INTERVAL,
    LINKS_CSV,
)
from data_pipeline.movie_models import MovieData
from data_pipeline.storage.checkpoint import CheckpointData, CheckpointManager
from data_pipeline.storage.parquet_writer import ParquetWriter

from common.clients.imdb import IMDBClient
from common.clients.tmdb import TMDBClient
from common.logger import get_logger
from common.services.field_extractor import extract_movie_fields

logger = get_logger(__name__)


class EnrichmentService:
    """
    Service for enriching movie metadata from TMDB and IMDb.

    Coordinates API clients, manages checkpoints, and handles failures.
    """

    def __init__(
        self,
        tmdb_client: TMDBClient,
        imdb_client: IMDBClient,
        checkpoint_manager: CheckpointManager,
        parquet_writer: ParquetWriter,
    ):
        """
        Initialize enrichment service.

        Args:
            tmdb_client: TMDB API client
            imdb_client: IMDb API client
            checkpoint_manager: Checkpoint manager for progress tracking
            parquet_writer: Parquet writer for results
        """
        self.tmdb_client = tmdb_client
        self.imdb_client = imdb_client
        self.checkpoint_manager = checkpoint_manager
        self.parquet_writer = parquet_writer

    async def enrich_movie(
        self,
        movie_id: int,
        tmdb_id: int,
    ) -> MovieData | None:
        """
        Enrich a single movie by fetching data from APIs.

        Args:
            movie_id: Original MovieLens movie ID
            tmdb_id: TMDB movie identifier

        Returns:
            MovieData object or None if enrichment failed (or either API failed)
        """
        try:
            # Fetch TMDB data (includes keywords and credits)
            tmdb_data = await self.tmdb_client.fetch_movie_full(tmdb_id)

            # Extract IMDb ID from TMDB response
            imdb_id = tmdb_data.get("imdb_id")

            if not imdb_id:
                logger.warning(
                    f"Movie {movie_id} (TMDB: {tmdb_id}) has no IMDb ID. Marking as failed."
                )
                return None

            # Fetch IMDb data
            imdb_data = await self.imdb_client.fetch_rating(imdb_id)

            if not imdb_data:
                logger.warning(
                    f"IMDb fetch failed for {movie_id} (IMDb: {imdb_id}). Marking as failed."
                )
                return None

            # Extract and normalize fields
            movie_data = extract_movie_fields(movie_id, tmdb_data, imdb_data)

            logger.debug(f"Successfully enriched movie {movie_id} (TMDB: {tmdb_id})")
            return movie_data

        except Exception as e:
            logger.error(
                f"Failed to enrich movie {movie_id} (TMDB: {tmdb_id}): "
                f"{type(e).__name__}: {str(e)}"
            )
            return None

    async def enrich_batch(
        self,
        movies: list[tuple[int, int]],
    ) -> tuple[list[MovieData], list[int]]:
        """
        Enrich a batch of movies concurrently.

        Args:
            movies: List of (movie_id, tmdb_id) tuples

        Returns:
            Tuple of (successful MovieData objects, failed movie IDs)
        """
        tasks = [self.enrich_movie(movie_id, tmdb_id) for movie_id, tmdb_id in movies]

        results = await asyncio.gather(*tasks)

        successful = []
        failed = []

        for (movie_id, _), result in zip(movies, results, strict=True):
            if result is not None:
                successful.append(result)
            else:
                failed.append(movie_id)

        if failed:
            logger.warning(f"Failed to enrich {len(failed)} movies in this batch.")

        return successful, failed

    def load_movies_to_process(
        self,
        checkpoint: CheckpointData,
    ) -> pd.DataFrame:
        """
        Load movies from CSV that need processing based on checkpoint.

        Args:
            checkpoint: Current checkpoint data

        Returns:
            DataFrame with movies to process
        """
        logger.info(f"Loading movies from {LINKS_CSV}")

        if not LINKS_CSV.exists():
            raise FileNotFoundError(f"Links file not found: {LINKS_CSV}")

        df = pd.read_csv(LINKS_CSV)

        # Filter out movies already processed
        if checkpoint.last_processed_movie_id is not None:
            original_count = len(df)
            df = df[df["movieId"] > checkpoint.last_processed_movie_id]
            logger.info(
                f"Resuming from movie ID {checkpoint.last_processed_movie_id}: "
                f"{len(df)} movies remaining (skipped {original_count - len(df)})"
            )

        # Validate required columns
        required_cols = ["movieId", "tmdbId"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")

        # Drop rows with missing TMDB IDs
        before_drop = len(df)
        df = df.dropna(subset=["tmdbId"])
        dropped = before_drop - len(df)
        if dropped > 0:
            logger.warning(f"Dropped {dropped} movies with missing TMDB IDs")

        # Convert TMDB IDs to integers
        df["tmdbId"] = df["tmdbId"].astype(int)

        logger.info(f"Total movies to process: {len(df)}")
        return df

    async def run(
        self,
        batch_size: int = 50,
        retry_failed: bool = True,
    ) -> None:
        """
        Run the complete enrichment pipeline.

        Args:
            batch_size: Number of movies to process concurrently
            retry_failed: Whether to retry failed movies at the end
        """
        logger.info("=" * 60)
        logger.info("Starting movie enrichment pipeline")
        logger.info("=" * 60)

        # Load checkpoint
        checkpoint = self.checkpoint_manager.load()

        # Load movies to process
        movies_df = self.load_movies_to_process(checkpoint)

        if movies_df.empty:
            logger.info("No movies to process. Pipeline complete!")
            return

        # Convert to list of tuples
        movies = list(zip(movies_df["movieId"], movies_df["tmdbId"], strict=True))
        total_movies = len(movies)

        # Process movies
        processed_count = 0

        for i in range(0, total_movies, batch_size):
            batch = movies[i : i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (total_movies + batch_size - 1) // batch_size

            logger.info(
                f"Processing batch {batch_num}/{total_batches} ({len(batch)} movies)"
            )

            # Enrich batch
            successful, failed = await self.enrich_batch(batch)

            # Write successful results
            for movie_data in successful:
                self.parquet_writer.add(movie_data)
                checkpoint.last_processed_movie_id = movie_data.movie_id
                checkpoint.processed_count += 1
                processed_count += 1

                # IMPORTANT: Remove from failed set if it's now successful
                checkpoint.failed_movie_ids.discard(movie_data.movie_id)

                # Periodic checkpoint save
                if processed_count % CHECKPOINT_INTERVAL == 0:
                    self.checkpoint_manager.save(checkpoint)

            # Track failed movies
            checkpoint.failed_movie_ids.update(failed)

            logger.info(
                f"Batch {batch_num} complete: "
                f"{len(successful)} successful, {len(failed)} failed"
            )

            # Save checkpoint after each batch
            self.checkpoint_manager.save(checkpoint)

        # Flush any remaining buffered data
        self.parquet_writer.close()

        # Retry failed movies if requested
        if retry_failed and checkpoint.failed_movie_ids:
            logger.info(f"Retrying {len(checkpoint.failed_movie_ids)} failed movies...")
            await self._retry_failed_movies(checkpoint, movies_df)

        # Final checkpoint save
        self.checkpoint_manager.save(checkpoint)
        self.checkpoint_manager.save_failed_movies(checkpoint.failed_movie_ids)

        # Summary
        logger.info("=" * 60)
        logger.info("Enrichment pipeline completed")
        logger.info(f"Total movies processed: {checkpoint.processed_count}")
        logger.info(f"Failed movies: {len(checkpoint.failed_movie_ids)}")
        logger.info("=" * 60)

    async def _retry_failed_movies(
        self,
        checkpoint: CheckpointData,
        movies_df: pd.DataFrame,
    ) -> None:
        """
        Retry processing failed movies.

        Args:
            checkpoint: Current checkpoint with failed IDs
            movies_df: Original movies DataFrame
        """
        failed_movies = [
            (row["movieId"], row["tmdbId"])
            for _, row in movies_df.iterrows()
            if row["movieId"] in checkpoint.failed_movie_ids
        ]

        if not failed_movies:
            return

        logger.info(f"Retrying {len(failed_movies)} failed movies...")

        successful, still_failed = await self.enrich_batch(failed_movies)

        # Write successful retries
        for movie_data in successful:
            self.parquet_writer.add(movie_data)
            checkpoint.processed_count += 1
            checkpoint.failed_movie_ids.discard(movie_data.movie_id)

        self.parquet_writer.flush()

        logger.info(
            f"Retry complete: {len(successful)} recovered, "
            f"{len(still_failed)} still failed"
        )
