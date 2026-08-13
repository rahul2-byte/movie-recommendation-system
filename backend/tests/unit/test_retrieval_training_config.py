from pathlib import Path

from training.retrieval.build_als import load_als_training_config
from training.retrieval.build_item_graph import load_item_graph_training_config
from training.retrieval.build_tfidf import (
    load_content_training_config,
    load_tfidf_training_config,
)
from training.retrieval.build_two_tower import load_two_tower_training_config


def test_loads_tfidf_training_config_relative_to_config_file(tmp_path: Path):
    config_path = tmp_path / "retrieval_training.yaml"
    config_path.write_text(
        """tfidf:
  dataset_version: fixture-v1
  output_dir: ../artifacts/models/tfidf
  text_fields: [title, overview]
  min_df: 1
  max_features: 100
  embedding_dim: 8
  random_seed: 42
  per_seed_candidates: 100
  mlflow_experiment_name: retrieval_training
""",
        encoding="utf-8",
    )

    config = load_tfidf_training_config(config_path)

    assert config.dataset_version == "fixture-v1"
    assert config.output_dir == (tmp_path.parent / "artifacts/models/tfidf").resolve()
    assert config.text_fields == ("title", "overview")
    assert config.embedding_dim == 8


def test_loads_content_training_config_with_field_weights(tmp_path: Path):
    config_path = tmp_path / "retrieval_training.yaml"
    config_path.write_text(
        """content:
  dataset_version: fixture-v1
  output_dir: ../artifacts/models/content
  text_fields: [title, overview, genres, release_year]
  field_weights: {title: 3, overview: 1, genres: 2, release_year: 1}
  min_df: 1
  max_features: 100
  embedding_dim: 8
  random_seed: 42
  per_seed_candidates: 100
  mlflow_experiment_name: retrieval_training
""",
        encoding="utf-8",
    )

    config = load_content_training_config(config_path)

    assert config.output_dir == (tmp_path.parent / "artifacts/models/content").resolve()
    assert config.field_weights == {
        "title": 3,
        "overview": 1,
        "genres": 2,
        "release_year": 1,
    }


def test_loads_als_training_config_relative_to_config_file(tmp_path: Path):
    config_path = tmp_path / "retrieval_training.yaml"
    config_path.write_text(
        """als:
  dataset_version: fixture-v1
  output_dir: ../artifacts/models/als
  factors: 8
  regularization: 0.1
  alpha: 20.0
  iterations: 2
  num_threads: 1
  random_seed: 42
  per_seed_candidates: 100
  parquet_batch_size: 1000
  mlflow_experiment_name: retrieval_training
""",
        encoding="utf-8",
    )

    config = load_als_training_config(config_path)

    assert config.output_dir == (tmp_path.parent / "artifacts/models/als").resolve()
    assert config.factors == 8
    assert config.num_threads == 1


def test_loads_two_tower_training_config_relative_to_config_file(tmp_path: Path):
    config_path = tmp_path / "retrieval_training.yaml"
    config_path.write_text(
        """two_tower:
  dataset_version: fixture-v1
  output_dir: ../artifacts/models/two_tower
  embedding_dim: 8
  batch_size: 4
  epochs: 1
  learning_rate: 0.01
  max_pairs_per_user: 10
  random_seed: 42
  per_seed_candidates: 100
  parquet_batch_size: 1000
  mlflow_experiment_name: retrieval_training
""",
        encoding="utf-8",
    )

    config = load_two_tower_training_config(config_path)

    assert (
        config.output_dir == (tmp_path.parent / "artifacts/models/two_tower").resolve()
    )
    assert config.embedding_dim == 8
    assert config.max_pairs_per_user == 10


def test_loads_item_graph_training_config_relative_to_config_file(tmp_path: Path):
    config_path = tmp_path / "retrieval_training.yaml"
    config_path.write_text(
        """item_graph:
  dataset_version: fixture-v1
  output_dir: ../artifacts/models/item_graph
  neighbor_count: 20
  k1: 1.2
  b: 0.75
  num_threads: 1
  random_seed: 42
  per_seed_candidates: 20
  parquet_batch_size: 1000
  mlflow_experiment_name: retrieval_training
""",
        encoding="utf-8",
    )

    config = load_item_graph_training_config(config_path)

    assert (
        config.output_dir == (tmp_path.parent / "artifacts/models/item_graph").resolve()
    )
    assert config.neighbor_count == 20
