"""MLflow experiment lookup helpers for legacy callers."""

import mlflow
from configuration.settings import MLFLOW_TRACKING_URI

mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)


def get_or_create_experiment(experiment_name: str) -> str:
    """Return an existing experiment ID or create the named experiment."""
    exp = mlflow.get_experiment_by_name(experiment_name)
    if exp:
        return exp.experiment_id

    return mlflow.create_experiment(
        name=experiment_name,
    )
