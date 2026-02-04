# backend/training/ranker.py
"""
Main training script for the LightGBM ranking model.

This script orchestrates the entire offline training pipeline:
1. Loads configuration.
2. Builds the query-centric training dataset.
3. Generates query-relative features.
4. Sets up an MLflow experiment.
5. Trains, evaluates, and logs a LightGBM ranker model.
"""
from pathlib import Path
import pandas as pd
import lightgbm as lgb
from sklearn.model_selection import GroupShuffleSplit
import logging
from typing import Dict, Any

from common.config import config
from tracking.mlflow_client import MlflowClient
from data.builder import build_ranking_dataset
from features.builder import FeatureBuilder

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

def _sanitize_metric_names(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitizes metric names by replacing invalid characters for MLflow.
    """
    sanitized_metrics = {}
    for key, value in metrics.items():
        # Replace '@' with '_at_' or simply remove it.
        # MLflow accepts alphanumerics, underscores, dashes, periods, spaces, colons, slashes.
        sanitized_key = key.replace('@', '_at_').replace('/', '_') # Example sanitization
        sanitized_metrics[sanitized_key] = value
    return sanitized_metrics


def train_ranker():
    """
    Orchestrates the training of the ranking model.
    """
    log.info("Loading configuration...")
    # Config is now loaded globally via backend.utils.config.config

    # 2. Build Dataset
    log.info("Building ranking dataset...")
    build_ranking_dataset(
        ratings_path=config.system.ratings_path,
        output_path=config.system.training_dataset_path
    )
    df_train_raw = pd.read_parquet(config.system.training_dataset_path)

    # 3. Build Features
    log.info("Building features...")
    feature_builder = FeatureBuilder.from_paths(
        movies_path=config.system.movies_metadata_path,
        tags_path=config.system.tags_path
    )
    df_train_featured = feature_builder.build_features(df_train_raw)

    # Define feature columns and target
    feature_cols = list(config.features.ranker_features) # Load feature names from config
    target_col = "label"

    X = df_train_featured[feature_cols]
    y = df_train_featured[target_col]

    # For ranking, we need to group by query
    # We can create a unique query_id for each group of query_movie_ids
    df_train_featured["query_id"] = df_train_featured["query_movie_ids"].astype(str)
    queries = df_train_featured["query_id"]

    # Split data into train and validation sets, ensuring all items for a query
    # are in the same set.
    gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    train_idx, val_idx = next(gss.split(X, y, groups=queries))

    X_train, y_train, queries_train = X.iloc[train_idx], y.iloc[train_idx], queries.iloc[train_idx]
    X_val, y_val, queries_val = X.iloc[val_idx], y.iloc[val_idx], queries.iloc[val_idx]

    # Get group counts for LightGBM
    train_groups = queries_train.value_counts().sort_index().values
    val_groups = queries_val.value_counts().sort_index().values

    # 4. Setup MLflow
    log.info("Initializing MLflow client and starting run...")
    mlflow_client = MlflowClient(
        experiment_name=config.system.tracking.ranker_experiment_name,
        tracking_uri=config.system.tracking.tracking_uri
    )

    with mlflow_client.start_run() as run:
        log.info(f"MLflow Run ID: {run.info.run_id}")
        mlflow_client.log_params({"num_features": len(feature_cols)}) # Use log_params for multiple, or log_param for single
        
        # 5. Train Model
        log.info("Training LightGBM ranker...")
        # Load hyperparameters from config
        params: Dict[str, Any] = dict(config.ranker.model_params)
        mlflow_client.log_params(params)

        model = lgb.LGBMRanker(**params)

        model.fit(
            X_train,
            y_train,
            group=train_groups,
            eval_set=[(X_val, y_val)],
            eval_group=[val_groups],
            eval_at=config.ranker.eval_params.eval_at, # Load from config
            callbacks=[lgb.early_stopping(config.ranker.eval_params.early_stopping_rounds, verbose=False)], # Load from config
        )

        # Log evaluation metrics
        eval_results = model.best_score_
        if eval_results:
            sanitized_metrics = _sanitize_metric_names(eval_results["valid_0"])
            mlflow_client.log_metrics(sanitized_metrics)

        # 6. Log to MLflow
        log.info("Logging model and feature names to MLflow...")
        mlflow_client.log_model(model, "lgbm_ranker")
        
        # 7. Save locally
        local_model_path = Path(config.system.ranker_model_dir) / "lgbm_lambdarank.txt"
        local_model_path.parent.mkdir(parents=True, exist_ok=True)
        model.booster_.save_model(str(local_model_path))
        log.info(f"Saved local model to {local_model_path}")
        
        log.info("Training complete.")

if __name__ == "__main__":
    train_ranker()
