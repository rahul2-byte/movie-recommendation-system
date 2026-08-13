import logging
from datetime import datetime

import mlflow
import numpy as np
from common.config import config

# Access settings from global config
settings = config.settings
MLFLOW_TRACKING_URI = settings.MLFLOW_TRACKING_URI
TRACE_SAMPLE_SIZE = settings.TRACE_SAMPLE_SIZE
MLFLOW_EXPERIMENTS = settings.MLFLOW_EXPERIMENTS
MAX_BUFFER_SIZE = 1000
log = logging.getLogger(__name__)

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
# Logging hooks
# -------------------------------
def log_recommendation(trace: dict, latency_ms: int) -> None:
    """
    Called on every recommendation request.
    Aggregates data in memory.
    """
    if len(REQUEST_BUFFER) == MAX_BUFFER_SIZE:
        REQUEST_BUFFER.pop(0)
    if len(METRIC_BUFFER["latency_ms"]) == MAX_BUFFER_SIZE:
        METRIC_BUFFER["latency_ms"].pop(0)
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
    if not REQUEST_BUFFER:
        return

    try:
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        experiment = mlflow.get_experiment_by_name(MLFLOW_EXPERIMENTS["online"])
        experiment_id = (
            experiment.experiment_id
            if experiment
            else mlflow.create_experiment(MLFLOW_EXPERIMENTS["online"])
        )
        run_ts = datetime.utcnow()

        with mlflow.start_run(
            experiment_id=experiment_id,
            run_name=f"inference_{run_ts:%Y-%m-%d_%H-%M-%S}",
        ):
            mlflow.set_tag("env", "prod")
            mlflow.set_tag("run_type", "online_inference")
            mlflow.set_tag("run_date", run_ts.date().isoformat())
            mlflow.set_tag("run_hour", run_ts.hour)
            mlflow.log_param("ranking_model_version", "lgbm_v1")
            mlflow.log_param("als_version", "als_v1")
            mlflow.log_param("two_tower_version", "two_tower_v1")
            mlflow.log_param("faiss_index_version", "faiss_items_v1")
            mlflow.log_metric(
                "p50_latency_ms", float(np.percentile(METRIC_BUFFER["latency_ms"], 50))
            )
            mlflow.log_metric(
                "p95_latency_ms", float(np.percentile(METRIC_BUFFER["latency_ms"], 95))
            )
            mlflow.log_metric(
                "ctr_10", METRIC_BUFFER["clicked"] / max(1, METRIC_BUFFER["impressions"])
            )
            mlflow.log_dict(REQUEST_BUFFER[:TRACE_SAMPLE_SIZE], "sample_traces.json")
    except Exception:
        log.warning("MLflow telemetry flush failed; retaining buffered telemetry", exc_info=True)
        return

    # ---- reset buffers ----
    REQUEST_BUFFER.clear()
    METRIC_BUFFER["latency_ms"].clear()
    METRIC_BUFFER["clicked"] = 0
    METRIC_BUFFER["impressions"] = 0
