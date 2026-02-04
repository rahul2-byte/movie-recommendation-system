# backend/tracking/mlflow_client.py
"""
Standardized MLflow client for consistent experiment tracking.
"""
import mlflow
import logging
from typing import Dict, Any, Optional

from common.config import config

log = logging.getLogger(__name__)

class MlflowClient:
    """
    Encapsulates MLflow operations for consistent tracking.
    """
    def __init__(self, experiment_name: str, tracking_uri: Optional[str] = None):
        self.experiment_name = experiment_name
        self.tracking_uri = tracking_uri if tracking_uri else config.system.tracking.tracking_uri
        
        mlflow.set_tracking_uri(self.tracking_uri)
        mlflow.set_experiment(self.experiment_name)
        log.info(f"MLflow client initialized for experiment: '{self.experiment_name}' "
                 f"at URI: '{self.tracking_uri}'")

    def start_run(self, run_name: Optional[str] = None):
        """Starts a new MLflow run."""
        return mlflow.start_run(run_name=run_name)

    def log_params(self, params: Dict[str, Any]):
        """Logs a dictionary of parameters."""
        mlflow.log_params(params)

    def log_metrics(self, metrics: Dict[str, Any]):
        """Logs a dictionary of metrics."""
        mlflow.log_metrics(metrics)
        
    def log_model(self, model: Any, artifact_path: str, **kwargs):
        """Logs a model artifact."""
        # Use a specific MLflow flavor's log_model
        if "lightgbm" in str(type(model)).lower():
            mlflow.lightgbm.log_model(model, artifact_path, **kwargs)
        # Add other model types (e.g., sklearn, pytorch) as needed
        else:
            mlflow.pyfunc.log_model(python_model=model, artifact_path=artifact_path, **kwargs)
        log.info(f"Logged model to MLflow artifact path: {artifact_path}")

    def log_artifact(self, local_path: str, artifact_path: Optional[str] = None):
        """Logs a local file or directory as an artifact."""
        mlflow.log_artifact(local_path, artifact_path)
        log.info(f"Logged artifact '{local_path}' to '{artifact_path}'")
        
    def end_run(self, status: str = "FINISHED"):
        """Ends the current MLflow run."""
        mlflow.end_run(status=status)
