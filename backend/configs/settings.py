import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file for local development
# This line should be called only once at the application's entry point
# For libraries/modules, it's better to assume env vars are already loaded.
load_dotenv(override=True)

# --- Core Settings ---
# Environment type ('LOCAL' or 'PROD')
ENVIRONMENT = os.getenv("ENVIRONMENT", "PROD")

# Root directory of the project, assuming this script is in backend/configs
PROJECT_ROOT = Path(__file__).resolve().parent.parent.absolute()

# S3 Bucket for all data artifacts in production
S3_BUCKET = os.getenv("S3_BUCKET")
if ENVIRONMENT == "PROD" and not S3_BUCKET:
    raise ValueError("S3_BUCKET must be set in PROD environment.")

# --- Path Definitions based on Environment ---
# Base path for data (local directory or S3 prefix)
_LOCAL_DATA_PATH = PROJECT_ROOT / os.getenv("LOCAL_DATA_PATH", "data")
_LOCAL_MLRUNS_PATH = (PROJECT_ROOT / os.getenv("LOCAL_MLRUNS_PATH", "mlruns")).absolute()

if ENVIRONMENT == "LOCAL":
    DATA_BASE_PATH = _LOCAL_DATA_PATH
    MLFLOW_TRACKING_URI = _LOCAL_MLRUNS_PATH.as_uri()
else: # PROD
    DATA_BASE_PATH = f"s3://{S3_BUCKET}"
    # Ensure DATA_BASE_PATH is string for f-string if it was Path
    DATA_BASE_STR = str(DATA_BASE_PATH)
    MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", f"file:{DATA_BASE_STR}/mlruns") # Default to S3 for artifacts

# --- Derived Paths ---
PROCESSED_DATA_PATH = f"{DATA_BASE_PATH}/processed"
RAW_DATA_PATH = f"{DATA_BASE_PATH}/raw"

if ENVIRONMENT == "LOCAL":
    # In LOCAL, artifacts are in the project root under 'artifacts'
    INDICES_PATH = f"{PROJECT_ROOT}/artifacts/indices"
    MODELS_PATH = f"{PROJECT_ROOT}/artifacts/models"
else:
    # In PROD (S3), we might keep them under data or a separate artifacts prefix
    # For now, let's assume they are stored under the bucket root
    INDICES_PATH = f"{DATA_BASE_PATH}/artifacts/indices"
    MODELS_PATH = f"{DATA_BASE_PATH}/artifacts/models"

INTERMEDIATE_DIR = Path(f"{DATA_BASE_PATH}/intermediate")

# Specific artifact locations
MOVIES_METADATA_PATH = f"{PROCESSED_DATA_PATH}/movies_enriched.parquet"
FAISS_INDEX_PATH = f"{INDICES_PATH}/als/faiss.index" # Example, could be dynamic
RANKER_MODEL_URI = f"{MODELS_PATH}/ranker" # MLflow model URI path
LINKS_CSV = Path(f"{RAW_DATA_PATH}/links.csv")

# --- Other Configurations ---
# Example: TOP_N_TAGS for feature building, from environment or default
TOP_N_TAGS = int(os.getenv("TOP_N_TAGS", 10_000))

# Example: CHUNK_SIZE for processing large datasets
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 50_000))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", 100))

# --- API Retry & Timeout Settings ---
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", 3))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", 1))
INITIAL_RETRY_DELAY = float(os.getenv("INITIAL_RETRY_DELAY", 0.5))
MAX_RETRY_DELAY = float(os.getenv("MAX_RETRY_DELAY", 2.0))
RETRY_EXPONENTIAL_BASE = float(os.getenv("RETRY_EXPONENTIAL_BASE", 1.5))
MAX_CONCURRENT_REQUESTS = int(os.getenv("MAX_CONCURRENT_REQUESTS", 10))

# --- TMDB Specific Settings ---
TMDB_BASE_URL = os.getenv("TMDB_BASE_URL", "https://api.themoviedb.org/3")
TMDB_ACCESS_TOKEN = os.getenv("TMDB_ACCESS_TOKEN")
TMDB_RATE_LIMIT = int(os.getenv("TMDB_RATE_LIMIT", 40)) # 40 requests per second
TMDB_IMAGE_BASE = os.getenv("TMDB_IMAGE_BASE", "https://image.tmdb.org/t/p")
TMDB_POSTER_SIZE = os.getenv("TMDB_POSTER_SIZE", "w342")

# --- IMDB Specific Settings ---
IMDB_BASE_URL = os.getenv("IMDB_BASE_URL", "http://www.omdbapi.com/")
IMDB_API_KEY = os.getenv("IMDB_API_KEY")
IMDB_RATE_LIMIT = int(os.getenv("IMDB_RATE_LIMIT", 20))
