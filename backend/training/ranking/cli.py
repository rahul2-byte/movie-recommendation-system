"""Train the leakage-safe LambdaRank artifact from immutable feature Parquet."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pyarrow.parquet as pq
from data_pipeline.tracking import load_tracking_config, tracked_run
from hashing import sha256

from training.progress import TerminalProgress
from training.ranking.config import load_ranking_training_config
from training.ranking.ranker_training import (
    evaluate_ranker,
    pack_ranking_features,
    read_feature_contract,
    train_ranker,
    validate_feature_compatibility,
)


def _default_config(name: str) -> Path:
    """Return a default ranking-training config path."""
    return Path(__file__).resolve().parents[2] / "configuration" / name


def _run_id() -> str:
    """Create a UTC run identifier for ranker artifacts."""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _packing_output_dir(root: Path, feature_dir: Path) -> Path:
    """Derive a cache path from the immutable feature parquet hash."""
    return root / sha256(feature_dir / "ranking_features.parquet")[:12]


def _pack_with_progress(feature_dir: Path, output_dir: Path, label: str):
    """Pack features while keeping progress off machine-readable stdout."""
    source = pq.ParquetFile(feature_dir / "ranking_features.parquet")
    progress = TerminalProgress(
        f"ranker {label} packing", source.metadata.num_row_groups
    )
    return pack_ranking_features(
        feature_dir,
        output_dir,
        progress_callback=lambda completed, _: progress.update(completed),
    )


def _metric_values(metrics: dict[str, dict[str, float]]) -> dict[str, float]:
    """Flatten nested model metrics for MLflow logging."""
    return {
        f"{ordering}_{name}": value
        for ordering, values in metrics.items()
        for name, value in values.items()
    }


def build_parser() -> argparse.ArgumentParser:
    """Build the ranker training and final-evaluation CLI parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-feature-dir", type=Path)
    parser.add_argument("--validation-feature-dir", type=Path)
    parser.add_argument("--test-feature-dir", type=Path)
    parser.add_argument("--ranker-artifact", type=Path)
    parser.add_argument(
        "--final-evaluation",
        action="store_true",
        help="Required acknowledgement before scoring the untouched test partition.",
    )
    parser.add_argument(
        "--config", type=Path, default=_default_config("ranking_training.yaml")
    )
    parser.add_argument(
        "--tracking-config", type=Path, default=_default_config("mlflow.yaml")
    )
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        help="Output directory; defaults to backend/artifacts/models/ranker/<UTC run ID>",
    )
    return parser


def main() -> None:
    """Train a LambdaRank artifact or evaluate one on untouched test data."""
    args = build_parser().parse_args()
    config = load_ranking_training_config(args.config)
    if args.test_feature_dir or args.ranker_artifact:
        if not args.test_feature_dir or not args.ranker_artifact:
            parser = build_parser()
            parser.error(
                "--test-feature-dir and --ranker-artifact must be used together"
            )
        if not args.final_evaluation:
            parser = build_parser()
            parser.error("Test evaluation requires --final-evaluation")
        test_feature_dir = args.test_feature_dir.resolve()
        ranker_artifact = args.ranker_artifact.resolve()
        contract = read_feature_contract(test_feature_dir)
        packing_root = (Path.cwd() / config.packed_data_dir).resolve()
        test = _pack_with_progress(
            test_feature_dir,
            _packing_output_dir(packing_root, test_feature_dir),
            "test",
        )
        feature_manifest = json.loads(
            (test_feature_dir / "manifest.json").read_text(encoding="utf-8")
        )
        dataset_version = str(feature_manifest.get("dataset_version", "pending"))
        with tracked_run(
            load_tracking_config(args.tracking_config),
            stage="ranking_test_evaluation",
            dataset_version=dataset_version,
            experiment_name=config.mlflow_experiment_name,
        ) as run:
            metrics = evaluate_ranker(ranker_artifact, test, contract, config)
            run.log_params(
                {
                    "ranker_artifact": str(ranker_artifact),
                    "test_feature_sha256": sha256(
                        test_feature_dir / "ranking_features.parquet"
                    ),
                    "feature_schema_version": contract.schema_version,
                    "command": " ".join(sys.argv),
                }
            )
            run.log_counts(
                {"test_rows": test.row_count, "test_queries": test.query_count}
            )
            run.log_metrics(_metric_values(metrics))
        print(
            json.dumps(
                {
                    "ranker_artifact": str(ranker_artifact),
                    "dataset_version": dataset_version,
                    "test_rows": test.row_count,
                    "test_metrics": metrics,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return
    if args.train_feature_dir is None or args.validation_feature_dir is None:
        parser = build_parser()
        parser.error(
            "Training requires --train-feature-dir and --validation-feature-dir"
        )
    train_feature_dir = args.train_feature_dir.resolve()
    validation_feature_dir = args.validation_feature_dir.resolve()
    contract = validate_feature_compatibility(train_feature_dir, validation_feature_dir)
    packing_root = (Path.cwd() / config.packed_data_dir).resolve()
    train = _pack_with_progress(
        train_feature_dir,
        _packing_output_dir(packing_root, train_feature_dir),
        "train",
    )
    validation = _pack_with_progress(
        validation_feature_dir,
        _packing_output_dir(packing_root, validation_feature_dir),
        "validation",
    )
    artifact_dir = (
        args.artifact_dir or Path.cwd() / "backend/artifacts/models/ranker" / _run_id()
    ).resolve()
    feature_manifest = json.loads(
        (train_feature_dir / "manifest.json").read_text(encoding="utf-8")
    )
    dataset_version = str(feature_manifest.get("dataset_version", "pending"))
    progress = TerminalProgress("ranker training", config.num_boost_round)
    with tracked_run(
        load_tracking_config(args.tracking_config),
        stage="ranking_train",
        dataset_version=dataset_version,
        experiment_name=config.mlflow_experiment_name,
    ) as run:
        run.log_params(
            {
                "train_feature_sha256": sha256(
                    train_feature_dir / "ranking_features.parquet"
                ),
                "validation_feature_sha256": sha256(
                    validation_feature_dir / "ranking_features.parquet"
                ),
                "training_config_sha256": sha256(config.path),
                "feature_schema_version": contract.schema_version,
                "command": " ".join(sys.argv),
            }
        )
        result = train_ranker(
            train,
            validation,
            contract,
            config,
            artifact_dir,
            progress_callback=lambda completed, _: progress.update(completed),
        )
        progress.stream.write("\n")
        run.log_counts(
            {
                "train_rows": train.row_count,
                "train_queries": train.query_count,
                "validation_rows": validation.row_count,
                "validation_queries": validation.query_count,
            }
        )
        run.log_metrics(_metric_values(result.validation_metrics))
        run.log_manifest(result.artifact_dir / "manifest.json")
        run.log_artifact(result.artifact_dir / "validation_metrics.json", "evaluation")
    print(
        json.dumps(
            {
                "artifact_dir": str(result.artifact_dir),
                "dataset_version": dataset_version,
                "train_rows": train.row_count,
                "validation_rows": validation.row_count,
                "validation_metrics": result.validation_metrics,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
