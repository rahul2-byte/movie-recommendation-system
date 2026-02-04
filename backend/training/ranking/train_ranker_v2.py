# backend/training/ranking/train_ranker_v2.py
import pandas as pd
import lightgbm as lgb
import numpy as np
import logging
import os
from pathlib import Path
from sklearn.model_selection import GroupShuffleSplit
from common.config import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger(__name__)

def train():
    data_path = "backend/data/processed/ranking_featured.parquet"
    model_dir = Path("backend/artifacts/models/ranker")
    model_dir.mkdir(parents=True, exist_ok=True)
    
    log.info(f"Loading featured dataset from {data_path}...")
    # Use pyarrow to read efficiently
    df = pd.read_parquet(data_path)
    
    # Define features
    feature_cols = [c for c in df.columns if c.startswith("feat_")]
    log.info(f"Features ({len(feature_cols)}): {feature_cols}")
    
    # 1. Grouped Random Split
    # Create query_id for grouping (hash of the list)
    df["query_id"] = df["query_movie_ids"].apply(lambda x: hash(tuple(x)))
    
    gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    train_idx, test_idx = next(gss.split(df, df["label"], groups=df["query_id"]))
    
    df_train = df.iloc[train_idx].sort_values("query_id")
    df_test = df.iloc[test_idx].sort_values("query_id")
    
    # 2. Prepare LightGBM Dataset
    q_train = df_train.groupby("query_id").size().values
    q_test = df_test.groupby("query_id").size().values
    
    dtrain = lgb.Dataset(
        df_train[feature_cols], 
        label=df_train["label"], 
        group=q_train
    )
    dtest = lgb.Dataset(
        df_test[feature_cols], 
        label=df_test["label"], 
        group=q_test,
        reference=dtrain
    )
    
    # 3. Train
    params = {
        "objective": "lambdarank",
        "metric": "ndcg",
        "ndcg_at": [10, 20],
        "learning_rate": 0.05,
        "num_leaves": 31,
        "feature_fraction": 0.8,
        "bagging_fraction": 0.8,
        "bagging_freq": 5,
        "verbose": -1
    }
    
    log.info("Starting LightGBM training...")
    model = lgb.train(
        params,
        dtrain,
        num_boost_round=500,
        valid_sets=[dtest],
        valid_names=["test"],
        callbacks=[
            lgb.early_stopping(stopping_rounds=20),
            lgb.log_evaluation(period=10)
        ]
    )
    
    # 4. Save
    model_path = model_dir / "lgbm_lambdarank.txt"
    model.save_model(str(model_path))
    log.info(f"✨ Model saved to {model_path} ✨")

if __name__ == "__main__":
    train()
