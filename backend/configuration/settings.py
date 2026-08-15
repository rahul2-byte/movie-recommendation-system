"""Environment-backed settings shared by local, training, and deployed runs."""

import json
import os
from pathlib import Path

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent.absolute()


class Settings(BaseSettings):
    """Validated application settings with safe local defaults."""

    ENVIRONMENT: str = "PROD"
    TMDB_ACCESS_TOKEN: str = ""
    IMDB_API_KEY: str = ""

    LOCAL_DATA_PATH: str = "data"
    LOCAL_MLRUNS_PATH: str = "mlruns"
    MODEL_BUNDLE_DIR: str = ""

    ALLOWED_ORIGINS: str | list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    REQUEST_TIMEOUT: int = 10
    MAX_RETRIES: int = 5
    MAX_CONCURRENT_REQUESTS: int = 50

    BATCH_SIZE: int = 100
    TOP_N_TAGS: int = 10000
    CHECKPOINT_INTERVAL: int = 100

    INITIAL_RETRY_DELAY: float = 1.0
    MAX_RETRY_DELAY: float = 5.0
    RETRY_EXPONENTIAL_BASE: float = 2.0

    TMDB_BASE_URL: str = "https://api.themoviedb.org/3"
    TMDB_RATE_LIMIT: int = 40

    IMDB_BASE_URL: str = "https://www.omdbapi.com/"
    IMDB_RATE_LIMIT: int = 20

    LOG_FORMAT_JSON: bool = True

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, value):
        """Accept list, JSON-list, or comma-separated CORS origins."""
        if isinstance(value, list):
            return [str(v).strip() for v in value if str(v).strip()]
        if value is None:
            return ["http://localhost:3000", "http://127.0.0.1:3000"]
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return ["http://localhost:3000", "http://127.0.0.1:3000"]
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    return [str(v).strip() for v in parsed if str(v).strip()]
            except json.JSONDecodeError:
                pass
            return [v.strip() for v in raw.split(",") if v.strip()]
        return ["http://localhost:3000", "http://127.0.0.1:3000"]

    @model_validator(mode="after")
    def reject_unsafe_production_cors(self) -> "Settings":
        """Reject wildcard CORS where credentialed browser requests are enabled."""
        if self.ENVIRONMENT.upper() != "LOCAL" and "*" in self.ALLOWED_ORIGINS:
            raise ValueError("ALLOWED_ORIGINS cannot contain '*' outside LOCAL")
        return self


settings = Settings()

# --- EXPORT AS GLOBALS FOR BACKWARD COMPATIBILITY ---
ENVIRONMENT = settings.ENVIRONMENT
TMDB_ACCESS_TOKEN = settings.TMDB_ACCESS_TOKEN
IMDB_API_KEY = settings.IMDB_API_KEY
REQUEST_TIMEOUT = settings.REQUEST_TIMEOUT
MAX_RETRIES = settings.MAX_RETRIES
MAX_CONCURRENT_REQUESTS = settings.MAX_CONCURRENT_REQUESTS
ALLOWED_ORIGINS = settings.ALLOWED_ORIGINS
BATCH_SIZE = settings.BATCH_SIZE
TOP_N_TAGS = settings.TOP_N_TAGS
CHECKPOINT_INTERVAL = settings.CHECKPOINT_INTERVAL
INITIAL_RETRY_DELAY = settings.INITIAL_RETRY_DELAY
MAX_RETRY_DELAY = settings.MAX_RETRY_DELAY
RETRY_EXPONENTIAL_BASE = settings.RETRY_EXPONENTIAL_BASE
TMDB_BASE_URL = settings.TMDB_BASE_URL
TMDB_RATE_LIMIT = settings.TMDB_RATE_LIMIT
IMDB_BASE_URL = settings.IMDB_BASE_URL
IMDB_RATE_LIMIT = settings.IMDB_RATE_LIMIT
LOG_FORMAT_JSON = settings.LOG_FORMAT_JSON
MODEL_BUNDLE_DIR = settings.MODEL_BUNDLE_DIR

# Derived Paths
if ENVIRONMENT == "LOCAL":
    DATA_BASE_PATH = PROJECT_ROOT / settings.LOCAL_DATA_PATH
    MLFLOW_TRACKING_URI = os.getenv(
        "MLFLOW_TRACKING_URI",
        f"sqlite:///{PROJECT_ROOT / 'mlflow.db'}",
    )
    INDICES_PATH = PROJECT_ROOT / "artifacts/indices"
    MODELS_PATH = PROJECT_ROOT / "artifacts/models"
else:
    MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "/tmp/mlruns")
    DATA_BASE_PATH = PROJECT_ROOT / settings.LOCAL_DATA_PATH
    INDICES_PATH = PROJECT_ROOT / "artifacts/indices"
    MODELS_PATH = PROJECT_ROOT / "artifacts/models"

PROCESSED_DATA_PATH = Path(DATA_BASE_PATH) / "processed"
RAW_DATA_PATH = Path(DATA_BASE_PATH) / "raw"
INTERMEDIATE_DIR = Path(DATA_BASE_PATH) / "intermediate"
LINKS_CSV = Path(f"{RAW_DATA_PATH}/links.csv")
RATINGS_PATH = f"{PROCESSED_DATA_PATH}/ratings.parquet"
MOVIES_METADATA_PATH = f"{PROCESSED_DATA_PATH}/movies_enriched.parquet"
TAGS_PATH = f"{PROCESSED_DATA_PATH}/tags.parquet"
CHECKPOINT_FILE = Path(f"{PROCESSED_DATA_PATH}/checkpoints/enrichment_checkpoint.json")
FAILED_MOVIES_FILE = Path(f"{PROCESSED_DATA_PATH}/checkpoints/failed_movies.json")
FAISS_INDEX_PATH = f"{INDICES_PATH}/als/faiss.index"
RANKER_MODEL_URI = f"{MODELS_PATH}/ranker"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p"
TMDB_POSTER_SIZE = "w342"
SCHEMA_VERSIONS_FILE = PROJECT_ROOT / "configuration/schemas/schema_versions.yaml"
