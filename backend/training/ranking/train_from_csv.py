# backend/training/ranking/train_from_csv.py
import lightgbm as lgb
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger(__name__)

def train():
    data_dir = Path("backend/training/ranking/native")
    model_dir = Path("backend/artifacts/models/ranker")
    model_dir.mkdir(parents=True, exist_ok=True)

    log.info("Loading training data from CSV...")
    # LightGBM will look for .query files automatically if we point to the CSV
    dtrain = lgb.Dataset(
        str(data_dir / "rank.train"),
        params={"two_pass": True, "header": False}
    )
    dtest = lgb.Dataset(
        str(data_dir / "rank.test"),
        reference=dtrain,
        params={"two_pass": True, "header": False}
    )

    params = {
        "objective": "lambdarank",
        "metric": "ndcg",
        "ndcg_at": [10, 20],
        "learning_rate": 0.05,
        "num_leaves": 31,
        "verbose": 1
    }

    log.info("Starting LightGBM training (Out-of-Core)...")
    model = lgb.train(
        params,
        dtrain,
        num_boost_round=100, # Reduced rounds for faster initial completion
        valid_sets=[dtest],
        valid_names=["test"],
        callbacks=[
            lgb.early_stopping(stopping_rounds=20),
            lgb.log_evaluation(period=10)
        ]
    )

    model.save_model(str(model_dir / "lgbm_lambdarank.txt"))
    log.info(f"✨ Model saved successfully! ✨")

if __name__ == "__main__":
    train()
