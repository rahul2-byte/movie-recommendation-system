# backend/training/ranking/train_from_csv.py
import logging
from pathlib import Path

import lightgbm as lgb

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
log = logging.getLogger(__name__)


def train():
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    data_dir = project_root / "backend/training/ranking/native"
    model_dir = project_root / "backend/artifacts/models/ranker"
    model_dir.mkdir(parents=True, exist_ok=True)

    log.info(f"Loading training data from {data_dir}...")
    # LightGBM will look for .query files automatically if we point to the CSV
    train_file = data_dir / "rank.train"
    test_file = data_dir / "rank.test"
    
    if not train_file.exists():
        log.error(f"Training file missing: {train_file}")
        return

    dtrain = lgb.Dataset(
        str(train_file), params={"two_pass": True, "header": False}
    )
    dtest = lgb.Dataset(
        str(test_file),
        reference=dtrain,
        params={"two_pass": True, "header": False},
    )

    params = {
        "objective": "lambdarank",
        "metric": "ndcg",
        "ndcg_at": [10, 20],
        "learning_rate": 0.05,
        "num_leaves": 31,
        "verbose": 1,
    }

    log.info("Starting LightGBM training (Out-of-Core)...")
    model = lgb.train(
        params,
        dtrain,
        num_boost_round=100,
        valid_sets=[dtest],
        valid_names=["test"],
        callbacks=[
            lgb.early_stopping(stopping_rounds=20),
            lgb.log_evaluation(period=5), # Log every 5 rounds instead of 10
        ],
    )

    model.save_model(str(model_dir / "lgbm_lambdarank.txt"))
    log.info(f"✨ Model saved successfully! ✨")


if __name__ == "__main__":
    train()
