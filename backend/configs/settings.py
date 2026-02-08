import os
from pathlib import Path
from typing import List, Optional, Dict
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent.absolute()

class Settings(BaseSettings):
    ENVIRONMENT: str = 'PROD'
    S3_BUCKET: str = 'movie-recommendation-system-artifacts'
    TMDB_ACCESS_TOKEN: str = ''
    IMDB_API_KEY: str = ''
    
    LOCAL_DATA_PATH: str = 'backend/data'
    LOCAL_MLRUNS_PATH: str = 'mlruns'
    
    ALLOWED_ORIGINS: List[str] = ['http://localhost:3000', 'http://127.0.0.1:3000']
    REQUEST_TIMEOUT: int = 10
    MAX_RETRIES: int = 5
    MAX_CONCURRENT_REQUESTS: int = 50
    
    BATCH_SIZE: int = 100
    TOP_N_TAGS: int = 10000
    CHECKPOINT_INTERVAL: int = 100
    
    INITIAL_RETRY_DELAY: float = 1.0
    MAX_RETRY_DELAY: float = 5.0
    RETRY_EXPONENTIAL_BASE: float = 2.0

    TMDB_BASE_URL: str = 'https://api.themoviedb.org/3'
    TMDB_RATE_LIMIT: int = 40
    
    IMDB_BASE_URL: str = 'http://www.omdbapi.com/'
    IMDB_RATE_LIMIT: int = 20

    LOG_FORMAT_JSON: bool = True
    TRACE_SAMPLE_SIZE: int = 2
    
    MLFLOW_EXPERIMENTS: Dict[str, str] = {
        'offline': 'recommender_offline_eval',
        'online': 'recommender_online_inference',
    }

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / '.env'),
        env_file_encoding='utf-8',
        extra='ignore'
    )

try:
    settings = Settings()
except Exception as e:
    print(f'Warning: Pydantic settings load failed ({e}), falling back to defaults/env.')
    class MockSettings:
        def __init__(self):
            self.ENVIRONMENT = os.getenv('ENVIRONMENT', 'PROD')
            self.S3_BUCKET = os.getenv('S3_BUCKET', '')
            self.TMDB_ACCESS_TOKEN = os.getenv('TMDB_ACCESS_TOKEN', '')
            self.IMDB_API_KEY = os.getenv('IMDB_API_KEY', '')
            self.REQUEST_TIMEOUT = 10
            self.MAX_RETRIES = 5
            self.MAX_CONCURRENT_REQUESTS = 50
            self.ALLOWED_ORIGINS = ['*']
            self.LOCAL_DATA_PATH = 'backend/data'
            self.LOCAL_MLRUNS_PATH = 'mlruns'
            self.BATCH_SIZE = 100
            self.TOP_N_TAGS = 10000
            self.CHECKPOINT_INTERVAL = 100
            self.INITIAL_RETRY_DELAY = 1.0
            self.MAX_RETRY_DELAY = 5.0
            self.RETRY_EXPONENTIAL_BASE = 2.0
            self.TMDB_BASE_URL = 'https://api.themoviedb.org/3'
            self.TMDB_RATE_LIMIT = 40
            self.IMDB_BASE_URL = 'http://www.omdbapi.com/'
            self.IMDB_RATE_LIMIT = 20
            self.LOG_FORMAT_JSON = True
            self.TRACE_SAMPLE_SIZE = 2
            self.MLFLOW_EXPERIMENTS = {
                'offline': 'recommender_offline_eval',
                'online': 'recommender_online_inference',
            }
    settings = MockSettings()

# --- EXPORT AS GLOBALS FOR BACKWARD COMPATIBILITY ---
ENVIRONMENT = settings.ENVIRONMENT
S3_BUCKET = settings.S3_BUCKET
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
TRACE_SAMPLE_SIZE = settings.TRACE_SAMPLE_SIZE
MLFLOW_EXPERIMENTS = settings.MLFLOW_EXPERIMENTS

# Derived Paths
if ENVIRONMENT == 'LOCAL':
    DATA_BASE_PATH = PROJECT_ROOT / settings.LOCAL_DATA_PATH
    MLFLOW_TRACKING_URI = (PROJECT_ROOT / settings.LOCAL_MLRUNS_PATH).as_uri()
    INDICES_PATH = PROJECT_ROOT / 'artifacts/indices'
    MODELS_PATH = PROJECT_ROOT / 'artifacts/models'
else:
    DATA_BASE_PATH = f's3://{S3_BUCKET}'
    MLFLOW_TRACKING_URI = os.getenv('MLFLOW_TRACKING_URI', f'file:{DATA_BASE_PATH}/mlruns')
    INDICES_PATH = f'{DATA_BASE_PATH}/artifacts/indices'
    MODELS_PATH = f'{DATA_BASE_PATH}/artifacts/models'

PROCESSED_DATA_PATH = f'{DATA_BASE_PATH}/processed'
RAW_DATA_PATH = f'{DATA_BASE_PATH}/raw'
INTERMEDIATE_DIR = Path(f'{DATA_BASE_PATH}/intermediate')
LINKS_CSV = Path(f'{RAW_DATA_PATH}/links.csv')
RATINGS_PATH = f'{PROCESSED_DATA_PATH}/ratings.parquet'
MOVIES_METADATA_PATH = f'{PROCESSED_DATA_PATH}/movies_enriched.parquet'
TAGS_PATH = f'{PROCESSED_DATA_PATH}/tags.parquet'
CHECKPOINT_FILE = Path(f'{PROCESSED_DATA_PATH}/checkpoints/enrichment_checkpoint.json')
FAILED_MOVIES_FILE = Path(f'{PROCESSED_DATA_PATH}/checkpoints/failed_movies.json')
FAISS_INDEX_PATH = f'{INDICES_PATH}/als/faiss.index'
RANKER_MODEL_URI = f'{MODELS_PATH}/ranker'
TMDB_IMAGE_BASE = 'https://image.tmdb.org/t/p'
TMDB_POSTER_SIZE = 'w342'
SCHEMA_VERSIONS_FILE = PROJECT_ROOT / 'configs/schemas/schema_versions.yaml'
