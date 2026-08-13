from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pandas as pd
from data_pipeline.config import (
    load_config,
    load_ranking_data_config,
    load_ranking_features_config,
)
from data_pipeline.manifests import sha256
from data_pipeline.ranking import (
    _limit_candidates_by_rrf,
    build_ranking_candidates,
    build_test_candidates,
    build_validation_candidates,
    materialize_ranking_features,
    prepare_ranking_data,
)


class _FakeArtifact:
    def __init__(
        self, train_sha256: str, candidates: dict[int, list[tuple[int, float]]]
    ):
        self.manifest = {
            "dataset_version": "fixture-version",
            "train_sha256": train_sha256,
        }
        self.candidates = candidates

    def retrieve_one(self, seed_tmdb_id: int, top_k: int) -> list[tuple[int, float]]:
        return self.candidates.get(seed_tmdb_id, [])[:top_k]


class _FailingArtifact(_FakeArtifact):
    def __init__(self, *args: object, failing_seed: int, **kwargs: object):
        super().__init__(*args, **kwargs)
        self.failing_seed = failing_seed

    def retrieve_one(self, seed_tmdb_id: int, top_k: int) -> list[tuple[int, float]]:
        if seed_tmdb_id == self.failing_seed:
            raise RuntimeError("simulated interruption")
        return super().retrieve_one(seed_tmdb_id, top_k)


def test_candidate_limit_uses_retrieval_ranks_not_labels():
    candidate_ids = pd.Series([10, 20, 30]).to_numpy(dtype="int64")
    source_rows = {
        "als": (
            pd.Series([10, 30]).to_numpy(dtype="int64"),
            pd.Series([1, 2]).to_numpy(dtype="int16"),
        ),
        "content": (
            pd.Series([20]).to_numpy(dtype="int64"),
            pd.Series([1]).to_numpy(dtype="int16"),
        ),
    }

    selected = _limit_candidates_by_rrf(candidate_ids, source_rows, candidate_limit=2)

    assert selected.tolist() == [10, 20]


def _write_data_config(path: Path) -> None:
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


def _write_ranking_config(path: Path, version_id: str) -> None:
    path.write_text(
        f"""
dataset_version: {version_id}
inner_train_fraction: 0.8
positive_rating_threshold: 3.0
seed_count: 5
candidate_k: 200
retrievers: [als, item_graph, two_tower]
compression: zstd
compression_level: 3
random_seed: 42
tracking:
  experiment_name: ranking_data
""".strip()
        + "\n",
        encoding="utf-8",
    )


def _write_ranking_features_config(path: Path) -> None:
    path.write_text(
        """
schema_version: ranking-features-v1
compression: zstd
compression_level: 3
features:
  - retrieval_source_count
  - retrieval_als_rank
  - retrieval_als_score_normalized
  - retrieval_item_graph_rank
  - retrieval_item_graph_score_normalized
  - retrieval_two_tower_rank
  - retrieval_two_tower_score_normalized
  - candidate_train_interaction_count
  - candidate_train_log_interaction_count
""".strip()
        + "\n",
        encoding="utf-8",
    )


def test_ranking_prepare_keeps_future_events_strictly_after_seed_history(
    tmp_path: Path,
):
    version_id = "fixture-version"
    data_config_path = tmp_path / "data_pipeline.yaml"
    ranking_config_path = tmp_path / "ranking_data.yaml"
    _write_data_config(data_config_path)
    _write_ranking_config(ranking_config_path, version_id)
    version_dir = tmp_path / "versions" / version_id
    version_dir.mkdir(parents=True)
    pd.DataFrame(
        {
            "user_id": [1] * 10 + [2] * 6 + [3] * 6,
            "tmdb_id": list(range(100, 110))
            + list(range(200, 206))
            + list(range(300, 306)),
            "movielens_id": list(range(1, 23)),
            "rating": [4.0] * 22,
            "timestamp": [1, 2, 3, 4, 5, 6, 7, 7, 8, 9] + [1, 2, 3, 4, 5, 6] + [1] * 6,
        }
    ).to_parquet(version_dir / "train.parquet", index=False)

    result = prepare_ranking_data(
        load_config(data_config_path),
        load_ranking_data_config(ranking_config_path),
        version_id,
    )

    retrieval = pd.read_parquet(result.output_dir / "retrieval_train.parquet")
    events = pd.read_parquet(result.output_dir / "ranking_events.parquet")
    assert set(retrieval["user_id"]) == {1, 2}
    assert set(events["user_id"]) == {1, 2}
    for user_id in (1, 2):
        assert retrieval.loc[retrieval["user_id"] == user_id, "timestamp"].max() < (
            events.loc[events["user_id"] == user_id, "timestamp"].min()
        )
    assert result.manifest["eligible_users"] == 2
    assert result.manifest["excluded_users"] == 1


def test_ranking_candidates_label_only_future_retrieved_movies_and_exclude_seeds(
    tmp_path: Path,
):
    version_id = "fixture-version"
    data_config_path = tmp_path / "data_pipeline.yaml"
    ranking_config_path = tmp_path / "ranking_data.yaml"
    _write_data_config(data_config_path)
    _write_ranking_config(ranking_config_path, version_id)
    version_dir = tmp_path / "versions" / version_id
    version_dir.mkdir(parents=True)
    pd.DataFrame(
        {
            "user_id": [1] * 8,
            "tmdb_id": list(range(100, 108)),
            "movielens_id": list(range(1, 9)),
            "rating": [4.0] * 8,
            "timestamp": list(range(1, 9)),
        }
    ).to_parquet(version_dir / "train.parquet", index=False)
    prepared = prepare_ranking_data(
        load_config(data_config_path),
        load_ranking_data_config(ranking_config_path),
        version_id,
    )
    train_sha256 = prepared.manifest["output_sha256"]["retrieval_train"]
    artifact = _FakeArtifact(
        train_sha256,
        {
            100: [(100, 1.0), (106, 0.9), (999, 0.2)],
            101: [(106, 0.8), (999, 0.1)],
            102: [(106, 0.7)],
            103: [(106, 0.6)],
            104: [(106, 0.5)],
            105: [(106, 0.4)],
        },
    )

    result = build_ranking_candidates(
        prepared.output_dir,
        load_ranking_data_config(ranking_config_path),
        {"als": artifact, "item_graph": artifact, "two_tower": artifact},
    )

    rows = pd.read_parquet(result.output_dir / "ranking_train.parquet")
    queries = pd.read_parquet(result.output_dir / "ranking_queries.parquet")
    assert set(rows["candidate_tmdb_id"]) == {106, 999}
    assert rows.loc[rows["candidate_tmdb_id"] == 106, "label"].eq(1).all()
    assert rows.loc[rows["candidate_tmdb_id"] == 999, "label"].eq(0).all()
    assert not set(rows["candidate_tmdb_id"]) & set(queries["seed_tmdb_ids"].iloc[0])
    assert "seed_tmdb_ids" not in rows
    assert set(rows["query_index"]) == {0}
    assert result.manifest["unretrieved_positive_targets"] == 1


def test_ranking_candidates_resume_from_completed_part(tmp_path: Path):
    version_id = "fixture-version"
    data_config_path = tmp_path / "data_pipeline.yaml"
    ranking_config_path = tmp_path / "ranking_data.yaml"
    _write_data_config(data_config_path)
    _write_ranking_config(ranking_config_path, version_id)
    version_dir = tmp_path / "versions" / version_id
    version_dir.mkdir(parents=True)
    pd.DataFrame(
        {
            "user_id": [1] * 8 + [2] * 8,
            "tmdb_id": list(range(100, 108)) + list(range(200, 208)),
            "movielens_id": list(range(1, 17)),
            "rating": [4.0] * 16,
            "timestamp": list(range(1, 9)) * 2,
        }
    ).to_parquet(version_dir / "train.parquet", index=False)
    ranking_config = replace(
        load_ranking_data_config(ranking_config_path),
        candidate_query_batch_size=1,
    )
    prepared = prepare_ranking_data(
        load_config(data_config_path), ranking_config, version_id
    )
    train_sha256 = prepared.manifest["output_sha256"]["retrieval_train"]
    candidates = {seed: [(999, 1.0)] for seed in range(100, 106)}
    candidates.update({seed: [(999, 1.0)] for seed in range(200, 206)})
    interrupted = _FailingArtifact(train_sha256, candidates, failing_seed=201)

    try:
        build_ranking_candidates(
            prepared.output_dir,
            ranking_config,
            {"als": interrupted, "item_graph": interrupted, "two_tower": interrupted},
        )
    except RuntimeError as error:
        assert str(error) == "simulated interruption"
    else:
        raise AssertionError("Expected simulated interruption")

    resumed = _FakeArtifact(train_sha256, candidates)
    result = build_ranking_candidates(
        prepared.output_dir,
        ranking_config,
        {"als": resumed, "item_graph": resumed, "two_tower": resumed},
    )

    assert result.manifest["query_count"] == 2
    assert set(
        pd.read_parquet(result.output_dir / "ranking_queries.parquet")["query_index"]
    ) == {0, 1}


def test_ranking_feature_materialization_is_chunked_and_schema_versioned(
    tmp_path: Path,
):
    version_id = "fixture-version"
    data_config_path = tmp_path / "data_pipeline.yaml"
    ranking_config_path = tmp_path / "ranking_data.yaml"
    feature_config_path = tmp_path / "ranking_features.yaml"
    _write_data_config(data_config_path)
    _write_ranking_config(ranking_config_path, version_id)
    _write_ranking_features_config(feature_config_path)
    version_dir = tmp_path / "versions" / version_id
    version_dir.mkdir(parents=True)
    pd.DataFrame(
        {
            "user_id": [1] * 8,
            "tmdb_id": list(range(100, 108)),
            "movielens_id": list(range(1, 9)),
            "rating": [4.0] * 8,
            "timestamp": list(range(1, 9)),
        }
    ).to_parquet(version_dir / "train.parquet", index=False)
    prepared = prepare_ranking_data(
        load_config(data_config_path),
        load_ranking_data_config(ranking_config_path),
        version_id,
    )
    artifact = _FakeArtifact(
        prepared.manifest["output_sha256"]["retrieval_train"],
        {seed: [(106, 1.0), (999, 0.1)] for seed in range(100, 106)},
    )
    candidates = build_ranking_candidates(
        prepared.output_dir,
        load_ranking_data_config(ranking_config_path),
        {"als": artifact, "item_graph": artifact, "two_tower": artifact},
    )

    result = materialize_ranking_features(
        candidates.output_dir,
        prepared.output_dir,
        load_ranking_features_config(feature_config_path),
    )

    frame = pd.read_parquet(result.output_dir / "ranking_features.parquet")
    schema = json.loads((result.output_dir / "feature_schema.json").read_text())
    assert list(frame["query_index"]) == sorted(frame["query_index"])
    assert result.manifest["feature_rows"] == len(frame)
    assert schema["schema_version"] == "ranking-features-v1"
    assert "user_id" not in frame


def test_validation_candidates_use_full_train_artifacts_without_target_leakage(
    tmp_path: Path,
):
    version_id = "fixture-version"
    ranking_config_path = tmp_path / "ranking_data.yaml"
    feature_config_path = tmp_path / "ranking_features.yaml"
    _write_ranking_config(ranking_config_path, version_id)
    _write_ranking_features_config(feature_config_path)
    version_dir = tmp_path / "versions" / version_id
    version_dir.mkdir(parents=True)
    train_path = version_dir / "train.parquet"
    pd.DataFrame(
        {
            "user_id": [1] * 8,
            "tmdb_id": list(range(100, 108)),
            "movielens_id": list(range(1, 9)),
            "rating": [4.0] * 8,
            "timestamp": list(range(1, 9)),
        }
    ).to_parquet(train_path, index=False)
    pd.DataFrame(
        {
            "query_id": ["validation:1"],
            "user_id": [1],
            "seed_tmdb_ids": [[100, 101, 102, 103, 104]],
            "ground_truth_tmdb_ids": [[106, 107]],
            "history_end_timestamp": [8],
            "ground_truth_start_timestamp": [9],
        }
    ).to_parquet(version_dir / "validation.parquet", index=False)
    artifact = _FakeArtifact(
        sha256(train_path),
        {seed: [(seed, 1.0), (106, 0.9), (999, 0.1)] for seed in range(100, 105)},
    )

    result = build_validation_candidates(
        version_dir,
        load_ranking_data_config(ranking_config_path),
        {"als": artifact, "item_graph": artifact, "two_tower": artifact},
    )

    rows = pd.read_parquet(result.output_dir / "ranking_validation.parquet")
    assert set(rows["candidate_tmdb_id"]) == {106, 999}
    assert rows.loc[rows["candidate_tmdb_id"] == 106, "label"].eq(1).all()
    assert result.manifest["partition"] == "validation"

    features = materialize_ranking_features(
        result.output_dir,
        version_dir,
        load_ranking_features_config(feature_config_path),
        candidate_file_name="ranking_validation.parquet",
        popularity_train_path=train_path,
    )
    assert features.manifest["feature_rows"] == len(rows)


def test_validation_candidates_records_zero_candidate_query(tmp_path: Path):
    version_id = "fixture-version"
    ranking_config_path = tmp_path / "ranking_data.yaml"
    _write_ranking_config(ranking_config_path, version_id)
    version_dir = tmp_path / "versions" / version_id
    version_dir.mkdir(parents=True)
    train_path = version_dir / "train.parquet"
    pd.DataFrame(
        {
            "user_id": [1] * 8,
            "tmdb_id": list(range(100, 108)),
            "movielens_id": list(range(1, 9)),
            "rating": [4.0] * 8,
            "timestamp": list(range(1, 9)),
        }
    ).to_parquet(train_path, index=False)
    pd.DataFrame(
        {
            "query_id": ["validation:1"],
            "user_id": [1],
            "seed_tmdb_ids": [[100, 101, 102, 103, 104]],
            "ground_truth_tmdb_ids": [[106, 107]],
            "history_end_timestamp": [8],
            "ground_truth_start_timestamp": [9],
        }
    ).to_parquet(version_dir / "validation.parquet", index=False)
    artifact = _FakeArtifact(sha256(train_path), {})

    result = build_validation_candidates(
        version_dir,
        load_ranking_data_config(ranking_config_path),
        {"als": artifact, "item_graph": artifact, "two_tower": artifact},
    )

    assert result.manifest["query_count"] == 1
    assert result.manifest["zero_candidate_queries"] == 1


def test_test_candidates_use_train_artifacts_and_test_queries(tmp_path: Path):
    version_id = "fixture-version"
    ranking_config_path = tmp_path / "ranking_data.yaml"
    _write_ranking_config(ranking_config_path, version_id)
    version_dir = tmp_path / "versions" / version_id
    version_dir.mkdir(parents=True)
    train_path = version_dir / "train.parquet"
    pd.DataFrame(
        {
            "user_id": [1] * 8,
            "tmdb_id": list(range(100, 108)),
            "movielens_id": list(range(1, 9)),
            "rating": [4.0] * 8,
            "timestamp": list(range(1, 9)),
        }
    ).to_parquet(train_path, index=False)
    pd.DataFrame(
        {
            "query_id": ["test:1"],
            "user_id": [1],
            "seed_tmdb_ids": [[100, 101, 102, 103, 104]],
            "ground_truth_tmdb_ids": [[106, 107]],
            "history_end_timestamp": [8],
            "ground_truth_start_timestamp": [9],
        }
    ).to_parquet(version_dir / "test.parquet", index=False)
    artifact = _FakeArtifact(
        sha256(train_path),
        {seed: [(seed, 1.0), (106, 0.9), (999, 0.1)] for seed in range(100, 105)},
    )

    result = build_test_candidates(
        version_dir,
        load_ranking_data_config(ranking_config_path),
        {"als": artifact, "item_graph": artifact, "two_tower": artifact},
    )

    rows = pd.read_parquet(result.output_dir / "ranking_test.parquet")
    assert set(rows["candidate_tmdb_id"]) == {106, 999}
    assert result.manifest["partition"] == "test"
