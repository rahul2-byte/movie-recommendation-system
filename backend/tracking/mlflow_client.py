import mlflow
import logging
from typing import Optional, Dict, Any

log = logging.getLogger(__name__)

class MlflowClient:
    def __init__(self, experiment_name: str, tracking_uri: str):
        self.experiment_name = experiment_name
        # Transition to SQLite if it's a file URI
        if tracking_uri.startswith("file:"):
            # Use a fixed SQLite path in the backend folder
            self.tracking_uri = "sqlite:///backend/mlflow.db"
        else:
            self.tracking_uri = tracking_uri
            
        mlflow.set_tracking_uri(self.tracking_uri)
        mlflow.set_experiment(self.experiment_name)
        log.info(f"MlflowClient: Tracking URI: {self.tracking_uri}, Experiment: {self.experiment_name}")

    def start_run(self, run_name: Optional[str] = None):
        return mlflow.start_run(run_name=run_name)

    def log_param(self, key: str, value: Any):
        mlflow.log_param(key, value)

    def log_params(self, params: Dict[str, Any]):
        mlflow.log_params(params)

    def log_metric(self, key: str, value: float, step: Optional[int] = None):
        mlflow.log_metric(key, value, step=step)

    def log_metrics(self, metrics: Dict[str, float], step: Optional[int] = None):
        mlflow.log_metrics(metrics, step=step)

    def log_model(self, model: Any, artifact_path: str):
        # Determine model flavor
        if hasattr(model, "save_model") and "lightgbm" in str(type(model)).lower():
            mlflow.lightgbm.log_model(model, artifact_path)
        elif hasattr(model, "state_dict"): # PyTorch
            mlflow.pytorch.log_model(model, artifact_path)
        else:
            mlflow.sklearn.log_model(model, artifact_path)