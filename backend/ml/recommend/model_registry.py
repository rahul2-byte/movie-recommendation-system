import lightgbm as lgb
from threading import Lock
from pathlib import Path
import pickle

_model = None
_lock = Lock()


def get_lgbm_model(model_path: str):
    global _model

    if _model is None:
        base_dir = Path(__file__).resolve().parents[2]  # backend/
        model_path = base_dir / "models" / "ranker" / "lgbm_lambdarank.txt"

        with open(model_path, "rb") as f:
            _model = pickle.load(f)  


    return _model