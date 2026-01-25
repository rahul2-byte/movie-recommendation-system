from pathlib import Path
from typing import Final
import os

# API Configuration
# TMDB_API_KEY: str = os.getenv("TMDB_API_KEY", "")
TMDB_ACCESS_TOKEN: str = os.getenv("TMDB_ACCESS_TOKEN", "")
IMDB_API_KEY: str = os.getenv("IMDB_API_KEY", "")

# Validate required environment variables
if not TMDB_ACCESS_TOKEN:
    raise RuntimeError(
        "TMDB_ACCESS_TOKEN not set. Please configure in .env file."
    )
if not IMDB_API_KEY:
    raise RuntimeError(
        "IMDB_API_KEY not set. Please configure in .env file."
    )

# API Endpoints
TMDB_BASE_URL: Final[str] = "https://api.themoviedb.org/3"
IMDB_BASE_URL: Final[str] = "https://www.omdbapi.com/"

# Request Configuration
REQUEST_TIMEOUT: Final[int] = 30
MAX_RETRIES: Final[int] = 5
INITIAL_RETRY_DELAY: Final[float] = 1.0
MAX_RETRY_DELAY: Final[float] = 30.0
RETRY_EXPONENTIAL_BASE: Final[float] = 2.0

# Concurrency Configuration
MAX_CONCURRENT_REQUESTS: Final[int] = 20
TMDB_RATE_LIMIT: Final[int] = 35  # requests per second
IMDB_RATE_LIMIT: Final[int] = 35  # requests per second

# Batch Processing
BATCH_SIZE: Final[int] = 500
CHECKPOINT_INTERVAL: Final[int] = 100  # Save checkpoint every N movies

# Path Configuration
DATA_DIR: Path = Path("./backend/data")
RAW_DIR: Path = DATA_DIR / "raw"
INTERMEDIATE_DIR: Path = DATA_DIR / "intermediate"
PROCESSED_DIR: Path = DATA_DIR / "processed"
LOG_DIR: Path = Path("../logs")

# Create directories if they don't exist
for directory in [INTERMEDIATE_DIR, PROCESSED_DIR, LOG_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# File Paths
LINKS_CSV: Path = RAW_DIR / "links.csv"
CHECKPOINT_FILE: Path = INTERMEDIATE_DIR / "checkpoint.json"
FAILED_MOVIES_FILE: Path = INTERMEDIATE_DIR / "failed_movies.json"
SCHEMA_VERSIONS_FILE: Path = Path("utils/config/schema_versions.yaml")

# Output Configuration
PARTITION_COLUMN: Final[str] = "release_year"
OUTPUT_DATASET_NAME: Final[str] = "movies_enriched"

# From backend/src/features/config.py
INTERACTIONS_PATH = PROCESSED_DIR / "ratings.parquet"
ITEM_META_PATH = PROCESSED_DIR / "movies_enriched.parquet"
OUTPUT_PATH = PROCESSED_DIR / "ranking_features.parquet"
MIN_USER_INTERACTIONS = 5
RECENT_K = 5