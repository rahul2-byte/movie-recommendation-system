# services/mlflow_logger.py

from datetime import datetime

import mlflow
import numpy as np
from common.config import config

# Access settings from global config
settings = config.settings
MLFLOW_TRACKING_URI = settings.MLFLOW_TRACKING_URI
TRACE_SAMPLE_SIZE = settings.TRACE_SAMPLE_SIZE
MLFLOW_EXPERIMENTS = settings.MLFLOW_EXPERIMENTS

from logger.services.mlflow_utils import get_or_create_experiment

# -------------------------------
# Buffers (in-memory aggregation)
# -------------------------------
REQUEST_BUFFER = []
METRIC_BUFFER = {
    "latency_ms": [],
    "clicked": 0,
    "impressions": 0,
}

# -------------------------------
# MLflow setup
# -------------------------------
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

# Resolve experiment ID from name (random ID handled by MLflow)
ONLINE_EXP_ID = get_or_create_experiment(MLFLOW_EXPERIMENTS["online"])


# -------------------------------
# Logging hooks
# -------------------------------
def log_recommendation(trace: dict, latency_ms: int) -> None:
    """
    Called on every recommendation request.
    Aggregates data in memory.
    """
    REQUEST_BUFFER.append(trace)
    METRIC_BUFFER["latency_ms"].append(latency_ms)
    METRIC_BUFFER["impressions"] += 1


def log_click() -> None:
    """Called on implicit user click."""
    METRIC_BUFFER["clicked"] += 1


# -------------------------------
# Periodic MLflow flush
# -------------------------------
def flush_to_mlflow() -> None:
    """
    Flushes aggregated metrics + sampled traces to MLflow.
    Should be called periodically (background task).
    """
    print("FLUSH CALLED")
    if not REQUEST_BUFFER:
        return

    run_ts = datetime.utcnow()

    with mlflow.start_run(
        experiment_id=ONLINE_EXP_ID,
        run_name=f"inference_{run_ts:%Y-%m-%d_%H-%M-%S}",
    ):
        # ---- tags (time-based indexing & filtering) ----
        mlflow.set_tag("env", "prod")
        mlflow.set_tag("run_type", "online_inference")
        mlflow.set_tag("run_date", run_ts.date().isoformat())
        mlflow.set_tag("run_hour", run_ts.hour)

        # ---- model lineage ----
        mlflow.log_param("ranking_model_version", "lgbm_v1")
        mlflow.log_param("als_version", "als_v1")
        mlflow.log_param("two_tower_version", "two_tower_v1")
        mlflow.log_param("faiss_index_version", "faiss_items_v1")

        # ---- aggregated metrics ----
        mlflow.log_metric(
            "p50_latency_ms",
            float(np.percentile(METRIC_BUFFER["latency_ms"], 50)),
        )
        mlflow.log_metric(
            "p95_latency_ms",
            float(np.percentile(METRIC_BUFFER["latency_ms"], 95)),
        )

        ctr = METRIC_BUFFER["clicked"] / max(1, METRIC_BUFFER["impressions"])
        mlflow.log_metric("ctr_10", ctr)

        # ---- sampled traces only ----
        mlflow.log_dict(
            REQUEST_BUFFER[:TRACE_SAMPLE_SIZE],
            "sample_traces.json",
        )

    # ---- reset buffers ----
    REQUEST_BUFFER.clear()
    METRIC_BUFFER["latency_ms"].clear()
    METRIC_BUFFER["clicked"] = 0
    METRIC_BUFFER["impressions"] = 0
