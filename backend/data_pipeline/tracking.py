"""MLflow orchestration wrapper for explicit ETL commands."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import mlflow
import yaml


@dataclass(frozen=True)
class TrackingConfig:
    local_store_dir: Path
    experiment_name: str


class StageRun:
    def __init__(self, run_id: str):
        self.run_id = run_id

    def log_counts(self, counts: dict[str, int]) -> None:
        mlflow.log_metrics({key: float(value) for key, value in counts.items()})

    def log_metrics(self, metrics: dict[str, float]) -> None:
        mlflow.log_metrics(metrics)

    def log_params(self, params: dict[str, str]) -> None:
        mlflow.log_params(params)

    def log_dataset_version(self, dataset_version: str) -> None:
        mlflow.set_tag("dataset_version", dataset_version)
        mlflow.log_param("resolved_dataset_version", dataset_version)

    def log_manifest(self, path: Path) -> None:
        mlflow.log_artifact(str(path), artifact_path="manifests")

    def log_artifact(self, path: Path, artifact_path: str = "artifacts") -> None:
        mlflow.log_artifact(str(path), artifact_path=artifact_path)


def load_tracking_config(path: Path) -> TrackingConfig:
    path = path.resolve()
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    tracking = payload.get("tracking") if isinstance(payload, dict) else None
    if not isinstance(tracking, dict):
        raise ValueError("tracking configuration must contain a tracking mapping")
    store = tracking.get("local_store_dir")
    experiment = tracking.get("data_pipeline_experiment_name")
    if (
        not isinstance(store, str)
        or not store
        or not isinstance(experiment, str)
        or not experiment
    ):
        raise ValueError(
            "tracking.local_store_dir and tracking.data_pipeline_experiment_name are required"
        )
    return TrackingConfig((path.parent / store).resolve(), experiment)


@contextmanager
def tracked_run(
    config: TrackingConfig,
    *,
    stage: str,
    dataset_version: str,
    experiment_name: str | None = None,
) -> Iterator[StageRun]:
    config.local_store_dir.mkdir(parents=True, exist_ok=True)
    database = config.local_store_dir / "mlflow.db"
    mlflow.set_tracking_uri(f"sqlite:///{database}")
    selected_experiment = experiment_name or config.experiment_name
    experiment = mlflow.get_experiment_by_name(selected_experiment)
    if experiment is None:
        experiment_id = mlflow.create_experiment(
            selected_experiment,
            artifact_location=(config.local_store_dir / "artifacts").as_uri(),
        )
    else:
        experiment_id = experiment.experiment_id
    with mlflow.start_run(experiment_id=experiment_id, run_name=f"data-{stage}") as run:
        mlflow.set_tags({"stage": stage, "dataset_version": dataset_version})
        mlflow.log_param("stage", stage)
        if dataset_version != "pending":
            mlflow.log_param("dataset_version", dataset_version)
        yield StageRun(run.info.run_id)
