import lightgbm as lgb
from threading import Lock
from pathlib import Path
import os
import boto3
from configs import settings
from common.logger import get_logger

log = get_logger(__name__)

_models = {}
_lock = Lock()

def ensure_local_path(remote_path: str) -> str:
    """
    If in PROD, ensures the artifact is downloaded from S3 to /tmp.
    Returns the local path to the artifact.
    """
    if settings.ENVIRONMENT != "PROD":
        return remote_path

    # Extract S3 key from s3://bucket/key
    if str(remote_path).startswith("s3://"):
        parts = str(remote_path).replace("s3://", "").split("/")
        bucket = parts[0]
        key = "/".join(parts[1:])
    else:
        # Fallback if path isn't prefixed
        bucket = settings.S3_BUCKET
        key = str(remote_path)

    local_path = Path("/tmp") / key
    
    if not local_path.exists():
        log.info(f"Downloading {remote_path} from S3 to {local_path}...")
        local_path.parent.mkdir(parents=True, exist_ok=True)
        s3 = boto3.client("s3")
        s3.download_file(bucket, key, str(local_path))
    
    return str(local_path)


def get_lgbm_model(model_path: str):
    global _models

    # Map remote S3 path to /tmp in PROD
    effective_path = ensure_local_path(model_path)

    with _lock:
        if effective_path not in _models:
            if not Path(effective_path).exists():
                raise FileNotFoundError(f"LGBM model not found at {effective_path}")
            
            _models[effective_path] = lgb.Booster(model_file=effective_path)

    return _models[effective_path]