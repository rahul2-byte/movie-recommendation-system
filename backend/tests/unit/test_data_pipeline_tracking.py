from __future__ import annotations

from pathlib import Path

from data_pipeline.tracking import load_tracking_config, tracked_run


def test_tracking_allows_a_prepare_run_to_set_its_resolved_dataset_version(
    tmp_path: Path,
):
    config_path = tmp_path / "mlflow.yaml"
    config_path.write_text(
        """
tracking:
  local_store_dir: mlflow
  data_pipeline_experiment_name: fixture-data-pipeline
""".strip()
        + "\n",
        encoding="utf-8",
    )

    config = load_tracking_config(config_path)
    with tracked_run(config, stage="prepare", dataset_version="pending") as run:
        run.log_dataset_version("fixture-123")
        run.log_counts({"catalog_rows": 2})

    assert (tmp_path / "mlflow" / "mlflow.db").is_file()


def test_tracking_allows_evaluation_to_use_a_separate_experiment(tmp_path: Path):
    config_path = tmp_path / "mlflow.yaml"
    config_path.write_text(
        """
tracking:
  local_store_dir: mlflow
  data_pipeline_experiment_name: fixture-data-pipeline
""".strip()
        + "\n",
        encoding="utf-8",
    )

    config = load_tracking_config(config_path)
    with tracked_run(
        config,
        stage="evaluation",
        dataset_version="fixture-123",
        experiment_name="fixture-evaluation",
    ) as run:
        run.log_params({"model_type": "popularity"})

    assert (tmp_path / "mlflow" / "mlflow.db").is_file()
