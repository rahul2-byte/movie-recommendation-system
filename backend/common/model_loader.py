import lightgbm as lgb
from threading import Lock
from pathlib import Path
import os
import time
import boto3
from botocore.config import Config
from boto3.s3.transfer import TransferConfig
from configs import settings
from common.logger import get_logger

log = get_logger(__name__)

_models = {}
_models_lock = Lock()
_download_lock = Lock()

s3_config = Config(
    retries={'max_attempts': 5, 'mode': 'standard'},
    connect_timeout=5,
    read_timeout=settings.REQUEST_TIMEOUT
)

def ensure_local_path(remote_path: str) -> str:
    if settings.ENVIRONMENT != 'PROD':
        return remote_path

    if str(remote_path).startswith('s3://'):
        parts = str(remote_path).replace('s3://', '').split('/')
        bucket = parts[0]
        key = '/'.join(parts[1:])
    else:
        bucket = settings.S3_BUCKET
        key = str(remote_path)

    local_path = Path('/tmp') / key

    if not local_path.exists():
        with _download_lock:
            if local_path.exists():
                return str(local_path)

            try:
                log.info(f'S3 Manager: Downloading {key} from {bucket}...')
                start_time = time.time()
                local_path.parent.mkdir(parents=True, exist_ok=True)
                s3 = boto3.client('s3', config=s3_config)
                transfer_config = TransferConfig(max_concurrency=10, use_threads=True)
                s3.download_file(Bucket=bucket, Key=key, Filename=str(local_path), Config=transfer_config)
                duration = time.time() - start_time
                file_size = local_path.stat().st_size / (1024 * 1024)
                log.info(f'S3 Manager: Successfully downloaded {key} ({file_size:.2f} MB) in {duration:.2f}s')
            except Exception as e:
                log.error(f'S3 Manager: Critical failure downloading {key}: {str(e)}')
                if local_path.exists(): local_path.unlink()
                raise

    return str(local_path)

def get_lgbm_model(model_path: str) -> lgb.Booster:
    global _models
    effective_path = ensure_local_path(model_path)
    with _models_lock:
        if effective_path not in _models:
            log.info(f'LGBM Loader: Loading model into memory from {effective_path}...')
            if not Path(effective_path).exists():
                raise FileNotFoundError(f'LGBM model not found at {effective_path}')
            _models[effective_path] = lgb.Booster(model_file=effective_path)
            log.info('LGBM Loader: Model loaded successfully.')
    return _models[effective_path]
