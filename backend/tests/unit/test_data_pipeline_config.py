from __future__ import annotations

from pathlib import Path

import pytest
from data_pipeline.config import ConfigError, load_config
from data_pipeline.manifests import dataset_version_id


def _write_config(path: Path, *, train_fraction: float = 0.6) -> None:
    path.write_text(
        f"""
dataset:
  name: movielens-32m
  schema_version: tmdb-keyed-v1
  raw_dir: data/raw
  enriched_metadata_path: data/raw/movies_enriched.parquet
  versions_dir: data/versions
prepare:
  compression: zstd
  compression_level: 3
  user_bucket_count: 4
split:
  train_fraction: {train_fraction}
  validation_fraction: 0.2
  positive_rating_threshold: 4.0
  min_positive_interactions: 10
  min_train_interactions: 6
  seed_count: 5
tracking:
  experiment_name: data_pipeline
  tracking_uri: sqlite:///artifacts/mlflow/mlflow.db
""".strip()
        + "\n",
        encoding="utf-8",
    )


def test_load_config_validates_split_rules_and_resolves_paths(tmp_path: Path):
    config_path = tmp_path / "data_pipeline.yaml"
    _write_config(config_path)

    config = load_config(config_path)

    assert config.dataset.raw_dir == tmp_path / "data/raw"
    assert config.split.seed_count == 5
    assert config.prepare.user_bucket_count == 4


def test_load_config_rejects_impossible_temporal_split(tmp_path: Path):
    config_path = tmp_path / "data_pipeline.yaml"
    _write_config(config_path, train_fraction=0.9)

    with pytest.raises(ConfigError, match="train_fraction \+ validation_fraction"):
        load_config(config_path)


def test_dataset_version_changes_when_input_or_config_changes(tmp_path: Path):
    config_path = tmp_path / "data_pipeline.yaml"
    _write_config(config_path)
    config = load_config(config_path)

    first = dataset_version_id(config, {"ratings.csv": "a"})
    changed_input = dataset_version_id(config, {"ratings.csv": "b"})
    config_path.write_text(
        config_path.read_text().replace("4.0", "4.5"), encoding="utf-8"
    )
    changed_config = dataset_version_id(load_config(config_path), {"ratings.csv": "a"})

    assert first.startswith("movielens-32m-")
    assert first != changed_input
    assert first != changed_config


def test_dataset_version_changes_when_pipeline_implementation_changes(tmp_path: Path):
    config_path = tmp_path / "data_pipeline.yaml"
    _write_config(config_path)
    config = load_config(config_path)

    first = dataset_version_id(
        config, {"ratings.csv": "a"}, implementation_fingerprint="implementation-a"
    )
    changed_implementation = dataset_version_id(
        config, {"ratings.csv": "a"}, implementation_fingerprint="implementation-b"
    )

    assert first != changed_implementation
