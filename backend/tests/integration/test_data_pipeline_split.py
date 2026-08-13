from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
from data_pipeline.config import load_config
from data_pipeline.manifests import sha256
from data_pipeline.prepare import prepare_dataset
from data_pipeline.split import (
    _partition_user_events,
    _records_for_bucket,
    split_dataset,
)
from data_pipeline.validate import validate_dataset


def _write_config(path: Path) -> None:
    path.write_text(
        """
dataset:
  name: fixture
  schema_version: tmdb-keyed-v1
  raw_dir: raw
  enriched_metadata_path: raw/movies_enriched.parquet
  versions_dir: versions
prepare:
  compression: zstd
  compression_level: 3
  user_bucket_count: 2
split:
  strategy: per_user_chronological
  train_fraction: 0.6
  validation_fraction: 0.2
  positive_rating_threshold: 3.0
  min_positive_interactions: 8
  min_train_interactions: 6
  seed_count: 5
""".strip()
        + "\n",
        encoding="utf-8",
    )


def _write_raw(raw_dir: Path) -> None:
    raw_dir.mkdir()
    movie_ids = list(range(1, 21))
    pd.DataFrame(
        {
            "movieId": movie_ids,
            "title": [str(i) for i in movie_ids],
            "genres": ["Drama"] * 20,
        }
    ).to_csv(raw_dir / "movies.csv", index=False)
    pd.DataFrame(
        {
            "movieId": movie_ids,
            "imdbId": movie_ids,
            "tmdbId": [1000 + i for i in movie_ids],
        }
    ).to_csv(raw_dir / "links.csv", index=False)
    ratings = []
    for user_id in (1, 2):
        for timestamp, movie_id in enumerate(range(1, 11), start=1):
            ratings.append(
                {
                    "userId": user_id,
                    "movieId": movie_id + (user_id - 1) * 10,
                    "rating": 4.0,
                    "timestamp": timestamp,
                }
            )
    pd.DataFrame(ratings).to_csv(raw_dir / "ratings.csv", index=False)
    pd.DataFrame(
        {"userId": [1], "movieId": [1], "tag": ["good"], "timestamp": [1]}
    ).to_csv(raw_dir / "tags.csv", index=False)
    pd.DataFrame(
        {
            "movie_id": movie_ids,
            "tmdb_id": [1000 + i for i in movie_ids],
            "title": [str(i) for i in movie_ids],
            "genres": [["Drama"]] * 20,
        }
    ).to_parquet(raw_dir / "movies_enriched.parquet", index=False)


def test_split_compacts_to_three_leakage_safe_files_and_resumes(tmp_path: Path):
    config_path = tmp_path / "data_pipeline.yaml"
    _write_config(config_path)
    _write_raw(tmp_path / "raw")
    config = load_config(config_path)
    prepared = prepare_dataset(config, chunk_size=7)

    first = split_dataset(config, prepared.version_id)

    train = pd.read_parquet(first.version_dir / "train.parquet")
    validation = pd.read_parquet(first.version_dir / "validation.parquet")
    test = pd.read_parquet(first.version_dir / "test.parquet")
    assert {path.name for path in first.version_dir.glob("*.parquet")} == {
        "catalog.parquet",
        "train.parquet",
        "validation.parquet",
        "test.parquet",
    }
    assert set(train["user_id"]) == {1, 2}
    assert all(len(seeds) == 5 for seeds in validation["seed_tmdb_ids"])
    assert all(len(seeds) == 5 for seeds in test["seed_tmdb_ids"])
    assert train.groupby("user_id").size().to_dict() == {1: 6, 2: 6}
    assert validation["ground_truth_tmdb_ids"].map(len).to_list() == [2, 2]
    assert test["ground_truth_tmdb_ids"].map(len).to_list() == [2, 2]
    assert validate_dataset(first.version_dir)["status"] == "complete"

    resumed = split_dataset(config, prepared.version_id)
    assert resumed.manifest["resumed_buckets"] == 2


def test_per_user_split_does_not_cut_through_equal_timestamps(tmp_path: Path):
    config_path = tmp_path / "data_pipeline.yaml"
    _write_config(config_path)
    config = load_config(config_path)
    events = pd.DataFrame(
        {
            "user_id": [1] * 12,
            "tmdb_id": list(range(1, 13)),
            "timestamp": [1, 2, 3, 4, 5, 6, 7, 7, 8, 9, 10, 11],
        }
    )

    train, validation, test = _partition_user_events(events, config, None, None)

    assert train["timestamp"].max() < validation["timestamp"].min()
    assert validation["timestamp"].max() < test["timestamp"].min()


def test_per_user_split_keeps_a_test_event_after_a_large_timestamp_group(
    tmp_path: Path,
):
    config_path = tmp_path / "data_pipeline.yaml"
    _write_config(config_path)
    config = load_config(config_path)
    events = pd.DataFrame(
        {
            "user_id": [1] * 31,
            "tmdb_id": list(range(1, 32)),
            "timestamp": list(range(1, 18)) + [18] * 10 + [19, 20, 21, 22],
        }
    )

    train, validation, test = _partition_user_events(events, config, None, None)

    assert train["timestamp"].max() < validation["timestamp"].min()
    assert validation["timestamp"].max() < test["timestamp"].min()


def test_split_excludes_users_before_partitioning_insufficient_history(tmp_path: Path):
    config_path = tmp_path / "data_pipeline.yaml"
    _write_config(config_path)
    config = load_config(config_path)
    events = pd.DataFrame(
        {
            "user_id": [1],
            "tmdb_id": [1001],
            "movielens_id": [1],
            "rating": [4.0],
            "timestamp": [1],
        }
    )

    train, validation, test, counts = _records_for_bucket(events, None, None, config)

    assert train.empty
    assert validation.empty
    assert test.empty
    assert counts["excluded_users"] == 1


def test_validate_rejects_query_with_non_strict_temporal_boundary(tmp_path: Path):
    config_path = tmp_path / "data_pipeline.yaml"
    _write_config(config_path)
    _write_raw(tmp_path / "raw")
    config = load_config(config_path)
    version_dir = split_dataset(
        config, prepare_dataset(config, chunk_size=7).version_id
    ).version_dir
    validation_path = version_dir / "validation.parquet"
    validation = pd.read_parquet(validation_path)
    validation.loc[0, "ground_truth_start_timestamp"] = validation.loc[
        0, "history_end_timestamp"
    ]
    validation.to_parquet(validation_path, index=False)
    manifest_path = version_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["output_sha256"]["validation"] = sha256(validation_path)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="strictly after history"):
        validate_dataset(version_dir)
