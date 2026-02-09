# backend/training/ranker.py
"""
Main training script for the LightGBM ranking model.
Uses pre-calculated features from the C++ Native pipeline.
"""

import logging
from pathlib import Path
from typing import Any, Dict

import lightgbm as lgb
import pandas as pd
from common.config import config
from sklearn.model_selection import GroupShuffleSplit
from tracking.mlflow_client import MlflowClient

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


def _sanitize_metric_names(metrics: Dict[str, Any]) -> Dict[str, Any]:
    sanitized_metrics = {}
    for key, value in metrics.items():
        sanitized_key = key.replace("@", "_at_").replace("/", "_")
        sanitized_metrics[sanitized_key] = value
    return sanitized_metrics


def train_ranker():
    log.info("Loading configuration...")

    # Load Pre-calculated Dataset (Parquet)
    dataset_path = Path("backend/data/processed/ranking_dataset.parquet")
    if not dataset_path.exists():
        log.error(f"Ranking dataset not found at {dataset_path}")
        return

    log.info(f"Loading ranking dataset from {dataset_path}...")
    df_train_featured = pd.read_parquet(dataset_path)
    log.info(f"Loaded {len(df_train_featured)} rows.")

    # Define feature columns
    # We use all columns starting with 'feat_'
    feature_cols = [c for c in df_train_featured.columns if c.startswith("feat_")]
    target_col = "label"

    log.info(f"Training with {len(feature_cols)} features: {feature_cols}")

    X = df_train_featured[feature_cols]
    y = df_train_featured[target_col]

    # Group by query for LambdaRank
    # query_movie_ids is a list, convert to tuple for hashing/grouping if needed,
    # but for GroupShuffleSplit we need a 1D array of group IDs.
    # We can assume adjacent rows with same query_movie_ids belong to same group if sorted?
    # No, we should create a hash/ID.
    df_train_featured["query_id_str"] = df_train_featured["query_movie_ids"].astype(str)
    queries = df_train_featured["query_id_str"]

    # Split data
    gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    train_idx, val_idx = next(gss.split(X, y, groups=queries))

    X_train, y_train, queries_train = (
        X.iloc[train_idx],
        y.iloc[train_idx],
        queries.iloc[train_idx],
    )
    X_val, y_val, queries_val = X.iloc[val_idx], y.iloc[val_idx], queries.iloc[val_idx]

    # Get group counts for LightGBM
    # Important: Data must be sorted by group for LightGBM group parameter to work correctly if passed as counts?
    # LightGBM requires data to be sorted by group if using 'group' file or parameter?
    # Yes, usually. Let's sort.

    log.info("Sorting training data by query group...")
    # Create a temporary df to sort
    train_df_sorted = pd.concat([X_train, y_train, queries_train], axis=1).sort_values(
        "query_id_str"
    )
    X_train = train_df_sorted[feature_cols]
    y_train = train_df_sorted[target_col]
    train_groups = train_df_sorted["query_id_str"].value_counts(sort=False).sort_index()
    # Ensure the order of counts matches the sorted dataframe groups
    # value_counts sort=False might not be enough.
    # Correct way: groupby().size() on the sorted dataframe, preserving order.
    train_groups = train_df_sorted.groupby("query_id_str", sort=False).size().values

    log.info("Sorting validation data by query group...")
    val_df_sorted = pd.concat([X_val, y_val, queries_val], axis=1).sort_values(
        "query_id_str"
    )
    X_val = val_df_sorted[feature_cols]
    y_val = val_df_sorted[target_col]
    val_groups = val_df_sorted.groupby("query_id_str", sort=False).size().values

    # Setup MLflow
    log.info("Initializing MLflow client...")
    mlflow_client = MlflowClient(
        experiment_name=config.system.tracking.ranker_experiment_name,
        tracking_uri=config.settings.MLFLOW_TRACKING_URI,
    )

    with mlflow_client.start_run() as run:
        log.info(f"MLflow Run ID: {run.info.run_id}")
        mlflow_client.log_params({"num_features": len(feature_cols)})
        mlflow_client.log_params({"train_rows": len(X_train), "val_rows": len(X_val)})

        # Train Model
        log.info("Training LightGBM ranker...")
        params: Dict[str, Any] = dict(config.ranker.model_params)
        mlflow_client.log_params(params)

        model = lgb.LGBMRanker(**params)

        model.fit(
            X_train,
            y_train,
            group=train_groups,
            eval_set=[(X_val, y_val)],
            eval_group=[val_groups],
            eval_at=config.ranker.eval_params.eval_at,
            callbacks=[
                lgb.early_stopping(
                    config.ranker.eval_params.early_stopping_rounds, verbose=False
                )
            ],
        )

        eval_results = model.best_score_
        if eval_results:
            sanitized_metrics = _sanitize_metric_names(eval_results["valid_0"])
            mlflow_client.log_metrics(sanitized_metrics)

        log.info("Logging model to MLflow...")
        mlflow_client.log_model(model, "lgbm_ranker")

        # Save locally
        local_model_path = Path(config.system.ranker_model_dir) / "lgbm_lambdarank.txt"
        local_model_path.parent.mkdir(parents=True, exist_ok=True)
        model.booster_.save_model(str(local_model_path))
        log.info(f"Saved local model to {local_model_path}")

        log.info("Training complete.")


if __name__ == "__main__":
    train_ranker()

