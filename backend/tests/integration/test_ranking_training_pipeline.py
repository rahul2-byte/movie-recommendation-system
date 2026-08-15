import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from training.ranking.cli import build_parser
from training.ranking.config import load_ranking_training_config
from training.ranking.ranker_training import (
    _rrf_scores,
    evaluate_ranker,
    pack_ranking_features,
    train_ranker,
    validate_feature_compatibility,
)


def _write_feature_artifact(
    directory: Path,
    *,
    feature_names: list[str],
    code_sha: str = "code",
    dataset_version: str = "dataset-v1",
) -> None:
    directory.mkdir()
    pd.DataFrame(
        {
            "query_index": [0, 0, 1, 1, 1],
            "candidate_tmdb_id": [10, 11, 12, 13, 14],
            "label": [1, 0, 0, 1, 0],
            "feature_b": [2.0, 3.0, 4.0, 5.0, 6.0],
            "feature_a": [10.0, 11.0, 12.0, 13.0, 14.0],
            "candidate_train_interaction_count": [5.0, 4.0, 3.0, 2.0, 1.0],
            "retrieval_als_rank": [1.0, 2.0, 1.0, 2.0, 3.0],
        }
    ).to_parquet(directory / "ranking_features.parquet", index=False)
    (directory / "feature_schema.json").write_text(
        json.dumps(
            {
                "schema_version": "ranking-features-v1",
                "feature_names": feature_names,
                "dataset_version": dataset_version,
                "config_sha256": "config",
                "code_sha256": code_sha,
            }
        ),
        encoding="utf-8",
    )
    (directory / "manifest.json").write_text(
        json.dumps(
            {
                "status": "complete",
                "schema_version": "ranking-features-v1",
                "feature_config_sha256": "config",
                "feature_code_sha256": code_sha,
            }
        ),
        encoding="utf-8",
    )


def test_pack_ranking_features_preserves_query_groups_and_schema_order(tmp_path):
    feature_dir = tmp_path / "features"
    _write_feature_artifact(feature_dir, feature_names=["feature_a", "feature_b"])

    packed = pack_ranking_features(feature_dir, tmp_path / "packed")

    assert packed.row_count == 5
    assert packed.query_count == 2
    assert packed.feature_dtype == "float16"
    assert packed.query_id_dtype == "int32"
    manifest = json.loads((packed.output_dir / "manifest.json").read_text())
    assert manifest["storage_dtypes"] == {"features": "float16", "query_ids": "int32"}
    assert np.load(packed.groups_path).tolist() == [2, 3]
    assert np.memmap(
        packed.features_path,
        dtype=packed.feature_dtype,
        mode="r",
        shape=(5, 2),
    ).astype(np.float32).tolist() == [
        [10.0, 2.0],
        [11.0, 3.0],
        [12.0, 4.0],
        [13.0, 5.0],
        [14.0, 6.0],
    ]


def test_validate_feature_compatibility_rejects_different_feature_code(tmp_path):
    train_dir = tmp_path / "train"
    validation_dir = tmp_path / "validation"
    _write_feature_artifact(train_dir, feature_names=["feature_a", "feature_b"])
    _write_feature_artifact(
        validation_dir, feature_names=["feature_a", "feature_b"], code_sha="other"
    )

    with pytest.raises(ValueError, match="feature_code_sha256"):
        validate_feature_compatibility(train_dir, validation_dir)


def test_validate_feature_compatibility_rejects_different_dataset_versions(tmp_path):
    train_dir = tmp_path / "train"
    validation_dir = tmp_path / "validation"
    _write_feature_artifact(train_dir, feature_names=["feature_a", "feature_b"])
    _write_feature_artifact(
        validation_dir,
        feature_names=["feature_a", "feature_b"],
        dataset_version="dataset-v2",
    )

    with pytest.raises(ValueError, match="dataset_version"):
        validate_feature_compatibility(train_dir, validation_dir)


def test_train_ranker_uses_packed_groups_and_writes_versioned_artifact(tmp_path):
    train_dir = tmp_path / "train"
    validation_dir = tmp_path / "validation"
    feature_names = [
        "feature_a",
        "candidate_train_interaction_count",
        "retrieval_als_rank",
    ]
    _write_feature_artifact(train_dir, feature_names=feature_names)
    _write_feature_artifact(validation_dir, feature_names=feature_names)
    contract = validate_feature_compatibility(train_dir, validation_dir)
    train = pack_ranking_features(train_dir, tmp_path / "packed-train")
    validation = pack_ranking_features(validation_dir, tmp_path / "packed-validation")
    config = replace(
        load_ranking_training_config(
            Path("backend/configuration/ranking_training.yaml")
        ),
        num_boost_round=10,
        early_stopping_rounds=3,
        min_data_in_leaf=1,
        num_leaves=3,
    )

    result = train_ranker(
        train,
        validation,
        contract,
        config,
        tmp_path / "model",
    )

    assert (result.artifact_dir / "model.txt").is_file()
    assert result.manifest["feature_names"] == feature_names
    assert set(result.validation_metrics) == {"popularity", "rrf", "lightgbm"}
    assert result.manifest["train_query_count"] == 2
    assert result.manifest["validation_query_count"] == 2


def test_evaluate_ranker_scores_immutable_feature_artifact(tmp_path):
    train_dir = tmp_path / "train"
    validation_dir = tmp_path / "validation"
    feature_names = [
        "feature_a",
        "candidate_train_interaction_count",
        "retrieval_als_rank",
    ]
    _write_feature_artifact(train_dir, feature_names=feature_names)
    _write_feature_artifact(validation_dir, feature_names=feature_names)
    contract = validate_feature_compatibility(train_dir, validation_dir)
    train = pack_ranking_features(train_dir, tmp_path / "packed-train")
    validation = pack_ranking_features(validation_dir, tmp_path / "packed-validation")
    config = replace(
        load_ranking_training_config(
            Path("backend/configuration/ranking_training.yaml")
        ),
        num_boost_round=10,
        early_stopping_rounds=3,
        min_data_in_leaf=1,
        num_leaves=3,
    )
    artifact = train_ranker(train, validation, contract, config, tmp_path / "model")

    metrics = evaluate_ranker(artifact.artifact_dir, validation, contract, config)

    assert set(metrics) == {"popularity", "rrf", "lightgbm"}


def test_ranker_cli_requires_explicit_immutable_feature_artifacts():
    args = build_parser().parse_args(
        [
            "--train-feature-dir",
            "train-features",
            "--validation-feature-dir",
            "validation-features",
        ]
    )

    assert args.train_feature_dir == Path("train-features")
    assert args.validation_feature_dir == Path("validation-features")


def test_rrf_baseline_uses_every_retrieval_rank_feature():
    features = np.array([[0.0, 1.0]], dtype=np.float32)

    scores = _rrf_scores(
        features,
        ("retrieval_als_rank", "retrieval_content_rank"),
        rank_constant=60,
    )

    assert scores.tolist() == pytest.approx([1.0 / 61.0])
