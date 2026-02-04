"""
Main entry point for the movie enrichment pipeline.

Orchestrates the complete workflow:
1. Load environment and configuration
2. Initialize API clients with connection pooling
3. Run enrichment service with checkpointing
4. Merge intermediate files into final dataset
"""

import argparse
import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Add backend dir to sys.path to allow for relative imports
BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from configs.settings import BATCH_SIZE, INTERMEDIATE_DIR, LINKS_CSV
from common.clients.imdb import IMDBClient
from common.clients.tmdb import TMDBClient
from common.logger import get_logger, log_separator
from common.services.enrichment import EnrichmentService
from common.storage.checkpoint import CheckpointManager
from common.storage.dataset_merger import merge_dataset
from common.storage.parquet_writer import ParquetWriter

logger = get_logger(__name__)


async def run_enrichment(
    batch_size: int = BATCH_SIZE,
    retry_failed: bool = True,
) -> None:
    """
    Run the enrichment pipeline with proper resource management.

    Args:
        batch_size: Number of movies to process concurrently
        retry_failed: Whether to retry failed movies
    """
    # Initialize API clients
    tmdb_client = TMDBClient()
    imdb_client = IMDBClient()

    try:
        # Start client sessions
        await tmdb_client.start()
        await imdb_client.start()

        # Initialize checkpoint and writer
        checkpoint_manager = CheckpointManager()
        parquet_writer = ParquetWriter()

        # Create enrichment service
        service = EnrichmentService(
            tmdb_client=tmdb_client,
            imdb_client=imdb_client,
            checkpoint_manager=checkpoint_manager,
            parquet_writer=parquet_writer,
        )

        # Run enrichment
        await service.run(
            batch_size=batch_size,
            retry_failed=retry_failed,
        )

    finally:
        # Cleanup resources
        await tmdb_client.close()
        await imdb_client.close()


def run_merge(
    strict_schema: bool = True,
    overwrite: bool = True,
) -> None:
    """
    Merge intermediate parquet files into final dataset.

    Args:
        strict_schema: If True, fail on schema mismatches
        overwrite: If True, overwrite existing dataset
    """
    try:
        merge_dataset(
            strict_schema=strict_schema,
            overwrite=overwrite,
        )
    except Exception as e:
        logger.error(f"Dataset merge failed: {e}")
        raise


def clear_intermediate_files() -> None:
    """Clear all intermediate files and checkpoints."""
    logger.info("Clearing intermediate files...")

    # Clear parquet batches
    batch_files = list(INTERMEDIATE_DIR.glob("movies_batch_*.parquet"))
    for file in batch_files:
        file.unlink()
        logger.info(f"Deleted {file.name}")

    # Clear checkpoint and failed movies
    checkpoint_manager = CheckpointManager()
    checkpoint_manager.clear()

    logger.info(f"Cleared {len(batch_files)} batch files")


async def retry_failed_movies_only(batch_size: int = BATCH_SIZE) -> None:
    """
    Retry only the failed movies from previous run.

    Args:
        batch_size: Number of movies to process concurrently
    """
    logger.info("=" * 60)
    logger.info("RETRYING FAILED MOVIES ONLY")
    logger.info("=" * 60)

    # Load checkpoint to get failed movie IDs
    checkpoint_manager = CheckpointManager()
    checkpoint = checkpoint_manager.load()

    if not checkpoint.failed_movie_ids:
        logger.info("No failed movies found in checkpoint. Nothing to retry!")
        return

    logger.info(f"Found {len(checkpoint.failed_movie_ids)} failed movies to retry")

    # Load original links to get TMDB IDs for failed movies
    if not LINKS_CSV.exists():
        raise FileNotFoundError(f"Links file not found: {LINKS_CSV}")

    import pandas as pd

    links_df = pd.read_csv(LINKS_CSV)

    # Filter to only failed movies
    failed_df = links_df[links_df["movieId"].isin(checkpoint.failed_movie_ids)]
    failed_df = failed_df.dropna(subset=["tmdbId"])
    failed_df["tmdbId"] = failed_df["tmdbId"].astype(int)

    if failed_df.empty:
        logger.warning("No valid TMDB IDs found for failed movies")
        return

    logger.info(f"Retrying {len(failed_df)} movies with valid TMDB IDs")

    # Initialize clients
    tmdb_client = TMDBClient()
    imdb_client = IMDBClient()

    try:
        await tmdb_client.start()
        await imdb_client.start()

        # Create new parquet writer for retry results
        parquet_writer = ParquetWriter()

        # Create enrichment service
        service = EnrichmentService(
            tmdb_client=tmdb_client,
            imdb_client=imdb_client,
            checkpoint_manager=checkpoint_manager,
            parquet_writer=parquet_writer,
        )

        # Convert to list of tuples
        movies = list(zip(failed_df["movieId"], failed_df["tmdbId"]))

        # Process in batches
        total_successful = 0
        still_failed = set()

        for i in range(0, len(movies), batch_size):
            batch = movies[i : i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(movies) + batch_size - 1) // batch_size

            logger.info(
                f"Processing retry batch {batch_num}/{total_batches} ({len(batch)} movies)"
            )

            successful, failed = await service.enrich_batch(batch)

            # Write successful results
            for movie_data in successful:
                parquet_writer.add(movie_data)
                checkpoint.failed_movie_ids.discard(movie_data.movie_id)
                total_successful += 1

            still_failed.update(failed)

            logger.info(
                f"Retry batch {batch_num}: {len(successful)} successful, {len(failed)} failed"
            )

        # Flush results
        parquet_writer.close()

        # Update checkpoint
        checkpoint_manager.save(checkpoint)
        checkpoint_manager.save_failed_movies(checkpoint.failed_movie_ids)

        # Summary
        logger.info("=" * 60)
        logger.info("RETRY COMPLETED")
        logger.info(f"Successfully recovered: {total_successful} movies")
        logger.info(f"Still failed: {len(still_failed)} movies")
        logger.info("=" * 60)

        if total_successful > 0:
            logger.info(f"New data written to intermediate parquet files")
            logger.info(f"Run 'python main.py --merge' to update final dataset")

    finally:
        await tmdb_client.close()
        await imdb_client.close()


async def run_full_pipeline(
    batch_size: int = BATCH_SIZE,
    retry_failed: bool = True,
    strict_schema: bool = True,
    overwrite: bool = True,
    clear_intermediate: bool = True,
) -> None:
    """
    Run complete pipeline: enrichment + merge.

    Args:
        batch_size: Number of movies to process concurrently
        retry_failed: Whether to retry failed movies
        strict_schema: If True, fail on schema mismatches during merge
        overwrite: If True, overwrite existing final dataset
        clear_intermediate: If True, delete intermediate files after merge
    """
    log_separator(logger, "=", 60)
    logger.info("MOVIE ENRICHMENT PIPELINE - FULL RUN")
    log_separator(logger, "=", 60)

    # Step 1: Enrichment
    logger.info("STEP 1: Running enrichment...")
    await run_enrichment(batch_size=batch_size, retry_failed=retry_failed)

    # Step 2: Merge
    logger.info("STEP 2: Merging dataset...")
    run_merge(strict_schema=strict_schema, overwrite=overwrite)

    # Step 3: Cleanup (optional)
    if clear_intermediate:
        logger.info("STEP 3: Cleaning up intermediate files...")
        clear_intermediate_files()

    log_separator(logger, "=", 60)
    logger.info("PIPELINE COMPLETED SUCCESSFULLY")
    log_separator(logger, "=", 60)


def main():
    """Main entry point with CLI argument parsing."""
    parser = argparse.ArgumentParser(
        description="Movie Enrichment Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
            Examples:
            # Run full pipeline (enrichment + merge)
            python main.py --full
            
            # Run only enrichment
            python main.py --enrich
            
            # Run only merge
            python main.py --merge
            
            # Clear intermediate files
            python main.py --clear
            
            # Run only retry for failed movies
            python main.py --retry-failed-only
            
            # Custom batch size
            python main.py --full --batch-size 100
            
            # Skip retry of failed movies
            python main.py --enrich --no-retry
        """,
    )

    # Mode selection (mutually exclusive)
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--full",
        action="store_true",
        help="Run full pipeline (enrichment + merge + cleanup)",
    )
    mode_group.add_argument("--enrich", action="store_true", help="Run enrichment only")
    mode_group.add_argument("--merge", action="store_true", help="Run merge only")
    mode_group.add_argument(
        "--clear", action="store_true", help="Clear intermediate files and checkpoints"
    )
    mode_group.add_argument(
        "--retry-failed-only",
        action="store_true",
        help="Retry only the failed movies from previous run",
    )

    # Enrichment options
    parser.add_argument(
        "--batch-size",
        type=int,
        default=BATCH_SIZE,
        help=f"Batch size for concurrent processing (default: {BATCH_SIZE})",
    )
    parser.add_argument(
        "--no-retry", action="store_true", help="Skip retry of failed movies"
    )

    # Merge options
    parser.add_argument(
        "--permissive-schema",
        action="store_true",
        help="Allow schema mismatches during merge (attempt casting)",
    )
    parser.add_argument(
        "--no-overwrite",
        action="store_true",
        help="Fail if output dataset already exists",
    )
    parser.add_argument(
        "--keep-intermediate",
        action="store_true",
        help="Keep intermediate files after merge (for debugging)",
    )

    args = parser.parse_args()

    try:
        if args.full:
            # Run full pipeline
            asyncio.run(
                run_full_pipeline(
                    batch_size=args.batch_size,
                    retry_failed=not args.no_retry,
                    strict_schema=not args.permissive_schema,
                    overwrite=not args.no_overwrite,
                    clear_intermediate=not args.keep_intermediate,
                )
            )

        elif args.enrich:
            # Run enrichment only
            asyncio.run(
                run_enrichment(
                    batch_size=args.batch_size,
                    retry_failed=not args.no_retry,
                )
            )

        elif args.merge:
            # Run merge only
            run_merge(
                strict_schema=not args.permissive_schema,
                overwrite=not args.no_overwrite,
            )

        elif args.clear:
            # Clear intermediate files
            clear_intermediate_files()

        elif args.retry_failed_only:
            # Retry only failed movies
            asyncio.run(
                retry_failed_movies_only(
                    batch_size=args.batch_size,
                )
            )

        logger.info("Process completed successfully")
        sys.exit(0)

    except KeyboardInterrupt:
        logger.warning("Process interrupted by user")
        sys.exit(130)

    except Exception as e:
        logger.error(f"Process failed: {type(e).__name__}: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()

