import pandas as pd
import logging
from pathlib import Path
import os

# Setup logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

DATA_DIR = Path("backend/data")
PROCESSED_DIR = DATA_DIR / "processed"
RAW_DIR = DATA_DIR / "raw"

def main():
    log.info("Starting data cleaning and filtering...")

    # 1. Load Enriched Movies (The Truth)
    movies_path = PROCESSED_DIR / "movies_enriched.parquet"
    if not movies_path.exists():
        log.error(f"Enriched movies not found at {movies_path}")
        return

    log.info(f"Loading enriched movies from {movies_path}...")
    movies_df = pd.read_parquet(movies_path)
    # Ensure column is movie_id
    if "movie_id" in movies_df.columns:
        valid_movie_ids = set(movies_df["movie_id"].unique())
    elif "movieId" in movies_df.columns:
        valid_movie_ids = set(movies_df["movieId"].unique())
    else:
        log.error("Could not find movie ID column in enriched movies.")
        return

    log.info(f"Found {len(valid_movie_ids)} valid enriched movies.")

    # 2. Filter Ratings
    ratings_parquet = PROCESSED_DIR / "ratings.parquet"
    ratings_raw = RAW_DIR / "ratings.csv"
    
    ratings_df = None
    if ratings_parquet.exists():
         log.info(f"Loading ratings from {ratings_parquet}...")
         ratings_df = pd.read_parquet(ratings_parquet)
    elif ratings_raw.exists():
         log.info(f"Loading ratings from {ratings_raw}...")
         ratings_df = pd.read_csv(ratings_raw)
    else:
        log.error("No ratings data found.")
        return

    original_ratings_count = len(ratings_df)
    ratings_df = ratings_df[ratings_df["movieId"].isin(valid_movie_ids)]
    filtered_ratings_count = len(ratings_df)
    log.info(f"Filtered ratings: {original_ratings_count} -> {filtered_ratings_count} (Dropped {original_ratings_count - filtered_ratings_count})")
    
    ratings_df.to_parquet(ratings_parquet, index=False)
    log.info(f"Saved filtered ratings to {ratings_parquet}")

    # 3. Filter Tags
    tags_parquet = PROCESSED_DIR / "tags.parquet"
    tags_raw = RAW_DIR / "tags.csv"

    tags_df = pd.DataFrame()
    if tags_parquet.exists():
         log.info(f"Loading tags from {tags_parquet}...")
         tags_df = pd.read_parquet(tags_parquet)
    elif tags_raw.exists():
         log.info(f"Loading tags from {tags_raw}...")
         tags_df = pd.read_csv(tags_raw)
    else:
        log.warning("No tags data found.")

    if not tags_df.empty:
        original_tags_count = len(tags_df)
        tags_df = tags_df[tags_df["movieId"].isin(valid_movie_ids)]
        filtered_tags_count = len(tags_df)
        log.info(f"Filtered tags: {original_tags_count} -> {filtered_tags_count}")
        tags_df.to_parquet(tags_parquet, index=False)
        log.info(f"Saved filtered tags to {tags_parquet}")

    # 4. Filter Links (Optional but good for consistency)
    links_parquet = PROCESSED_DIR / "links.parquet"
    links_raw = RAW_DIR / "links.csv"
    
    links_df = pd.DataFrame()
    if links_parquet.exists():
         links_df = pd.read_parquet(links_parquet)
    elif links_raw.exists():
         links_df = pd.read_csv(links_raw)
    
    if not links_df.empty:
        links_df = links_df[links_df["movieId"].isin(valid_movie_ids)]
        links_df.to_parquet(links_parquet, index=False)
        log.info(f"Saved filtered links to {links_parquet}")

    log.info("Data cleaning complete.")

if __name__ == "__main__":
    main()
