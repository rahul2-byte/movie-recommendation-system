"""Command line interface for the resumable offline data pipeline."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from training.retrieval.als_trainer import AlsArtifact
from training.retrieval.content_retriever import TfidfArtifact
from training.retrieval.item_graph_trainer import ItemGraphArtifact
from training.retrieval.two_tower_trainer import TwoTowerArtifact

from data_pipeline.config import (
    DataPipelineConfig,
    load_config,
    load_ranking_data_config,
    load_ranking_features_config,
)
from data_pipeline.prepare import prepare_dataset
from data_pipeline.ranking_dataset import (
    build_ranking_candidates,
    build_test_candidates,
    build_validation_candidates,
    materialize_ranking_features,
    prepare_ranking_data,
)
from data_pipeline.split import split_dataset
from data_pipeline.tracking import load_tracking_config, tracked_run
from data_pipeline.validate import validate_dataset


def _default_config(name: str) -> Path:
    """Return the checked-in default YAML path for a pipeline command."""
    return Path(__file__).resolve().parent.parent / "configuration" / name


def _resolve_version(
    config: DataPipelineConfig, requested: str | None, *, complete: bool
) -> str:
    """Resolve an explicit version or the latest complete dataset version."""
    if requested:
        return requested
    candidates = []
    for directory in config.dataset.versions_dir.glob("*"):
        marker = directory / (
            "manifest.json" if complete else ".work/prepare/prepare_manifest.json"
        )
        if marker.is_file():
            candidates.append(directory)
    if not candidates:
        status = "complete" if complete else "prepared"
        raise FileNotFoundError(
            f"No {status} dataset versions found in {config.dataset.versions_dir}"
        )
    return max(candidates, key=lambda path: path.stat().st_mtime).name


def main() -> None:
    """Dispatch data preparation, splitting, and validation commands."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s level=%(levelname)s %(message)s",
    )
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path, default=_default_config("data_pipeline.yaml")
    )
    parser.add_argument(
        "--tracking-config", type=Path, default=_default_config("mlflow.yaml")
    )
    subcommands = parser.add_subparsers(dest="command", required=True)
    prepare = subcommands.add_parser("prepare")
    prepare.add_argument("--chunk-size", type=int, default=1_000_000)
    split = subcommands.add_parser("split")
    split.add_argument("--dataset-version")
    ranking_prepare = subcommands.add_parser("ranking-prepare")
    ranking_prepare.add_argument("--dataset-version")
    ranking_prepare.add_argument(
        "--ranking-config", type=Path, default=_default_config("ranking_data.yaml")
    )
    ranking_candidates = subcommands.add_parser("ranking-candidates")
    ranking_candidates.add_argument("--ranking-data-dir", type=Path, required=True)
    ranking_candidates.add_argument(
        "--ranking-config", type=Path, default=_default_config("ranking_data.yaml")
    )
    ranking_candidates.add_argument("--als-artifact", type=Path, required=True)
    ranking_candidates.add_argument("--item-graph-artifact", type=Path, required=True)
    ranking_candidates.add_argument("--two-tower-artifact", type=Path, required=True)
    ranking_candidates.add_argument("--content-artifact", type=Path, required=True)
    ranking_validation = subcommands.add_parser("ranking-validation-candidates")
    ranking_validation.add_argument("--dataset-version")
    ranking_validation.add_argument(
        "--ranking-config", type=Path, default=_default_config("ranking_data.yaml")
    )
    ranking_validation.add_argument("--als-artifact", type=Path, required=True)
    ranking_validation.add_argument("--item-graph-artifact", type=Path, required=True)
    ranking_validation.add_argument("--two-tower-artifact", type=Path, required=True)
    ranking_validation.add_argument("--content-artifact", type=Path, required=True)
    ranking_test = subcommands.add_parser("ranking-test-candidates")
    ranking_test.add_argument("--dataset-version")
    ranking_test.add_argument(
        "--ranking-config", type=Path, default=_default_config("ranking_data.yaml")
    )
    ranking_test.add_argument("--als-artifact", type=Path, required=True)
    ranking_test.add_argument("--item-graph-artifact", type=Path, required=True)
    ranking_test.add_argument("--two-tower-artifact", type=Path, required=True)
    ranking_test.add_argument("--content-artifact", type=Path, required=True)
    ranking_features = subcommands.add_parser("ranking-features")
    ranking_features.add_argument("--ranking-candidate-dir", type=Path, required=True)
    ranking_features.add_argument("--ranking-data-dir", type=Path, required=True)
    ranking_features.add_argument(
        "--feature-config", type=Path, default=_default_config("ranking_features.yaml")
    )
    ranking_features.add_argument(
        "--candidate-file-name", default="ranking_train.parquet"
    )
    ranking_features.add_argument("--popularity-train-path", type=Path)
    validate = subcommands.add_parser("validate")
    validate.add_argument("--dataset-version")
    status = subcommands.add_parser("status")
    status.add_argument("--dataset-version")
    args = parser.parse_args()
    config = load_config(args.config)
    if args.command == "prepare":
        with tracked_run(
            load_tracking_config(args.tracking_config),
            stage="prepare",
            dataset_version="pending",
        ) as run:
            result = prepare_dataset(config, chunk_size=args.chunk_size)
            run.log_dataset_version(result.version_id)
            run.log_counts(
                {
                    key: value
                    for key, value in result.manifest.items()
                    if isinstance(value, int)
                }
            )
            run.log_manifest(result.work_dir / "prepare_manifest.json")
            print(json.dumps(result.manifest, indent=2, sort_keys=True))
        return
    if args.command == "split":
        version_id = _resolve_version(config, args.dataset_version, complete=False)
        with tracked_run(
            load_tracking_config(args.tracking_config),
            stage="split",
            dataset_version=version_id,
        ) as run:
            result = split_dataset(config, version_id)
            run.log_counts(
                {
                    key: value
                    for key, value in result.manifest.items()
                    if isinstance(value, int)
                }
            )
            run.log_manifest(result.version_dir / "manifest.json")
            print(json.dumps(result.manifest, indent=2, sort_keys=True))
        return
    if args.command == "ranking-prepare":
        ranking_config = load_ranking_data_config(args.ranking_config)
        version_id = args.dataset_version or ranking_config.dataset_version
        with tracked_run(
            load_tracking_config(args.tracking_config),
            stage="ranking_prepare",
            dataset_version=version_id,
            experiment_name=ranking_config.mlflow_experiment_name,
        ) as run:
            result = prepare_ranking_data(config, ranking_config, version_id)
            run.log_params(
                {
                    "ranking_config_sha256": result.manifest["ranking_config_sha256"],
                    "retrievers": ",".join(ranking_config.retrievers),
                }
            )
            run.log_counts(
                {
                    key: value
                    for key, value in result.manifest.items()
                    if isinstance(value, int)
                }
            )
            run.log_manifest(result.output_dir / "manifest.json")
            print(json.dumps(result.manifest, indent=2, sort_keys=True))
        return
    if args.command == "ranking-candidates":
        ranking_config = load_ranking_data_config(args.ranking_config)
        artifacts = {
            "als": AlsArtifact.load(args.als_artifact),
            "item_graph": ItemGraphArtifact.load(args.item_graph_artifact),
            "two_tower": TwoTowerArtifact.load(args.two_tower_artifact),
            "content": TfidfArtifact.load(args.content_artifact),
        }
        with tracked_run(
            load_tracking_config(args.tracking_config),
            stage="ranking_candidates",
            dataset_version=ranking_config.dataset_version,
            experiment_name=ranking_config.mlflow_experiment_name,
        ) as run:
            result = build_ranking_candidates(
                args.ranking_data_dir.resolve(), ranking_config, artifacts
            )
            run.log_params(
                {
                    "ranking_config_sha256": result.manifest["ranking_config_sha256"],
                    "candidate_k_per_source": str(
                        result.manifest["candidate_k_per_source"]
                    ),
                    "als_artifact": str(args.als_artifact.resolve()),
                    "item_graph_artifact": str(args.item_graph_artifact.resolve()),
                    "two_tower_artifact": str(args.two_tower_artifact.resolve()),
                    "content_artifact": str(args.content_artifact.resolve()),
                }
            )
            run.log_counts(
                {
                    key: value
                    for key, value in result.manifest.items()
                    if isinstance(value, int)
                }
            )
            run.log_manifest(result.output_dir / "manifest.json")
            print(json.dumps(result.manifest, indent=2, sort_keys=True))
        return
    if args.command == "ranking-features":
        feature_config = load_ranking_features_config(args.feature_config)
        candidate_manifest = json.loads(
            (args.ranking_candidate_dir / "manifest.json").read_text(encoding="utf-8")
        )
        with tracked_run(
            load_tracking_config(args.tracking_config),
            stage="ranking_features",
            dataset_version=candidate_manifest["dataset_version"],
        ) as run:
            result = materialize_ranking_features(
                args.ranking_candidate_dir,
                args.ranking_data_dir,
                feature_config,
                candidate_file_name=args.candidate_file_name,
                popularity_train_path=args.popularity_train_path,
            )
            run.log_params(
                {
                    "feature_config_sha256": result.manifest["feature_config_sha256"],
                    "feature_schema_version": result.manifest["schema_version"],
                }
            )
            run.log_counts(
                {
                    key: value
                    for key, value in result.manifest.items()
                    if isinstance(value, int)
                }
            )
            run.log_manifest(result.output_dir / "manifest.json")
            run.log_artifact(result.output_dir / "feature_schema.json")
            print(json.dumps(result.manifest, indent=2, sort_keys=True))
        return
    if args.command == "ranking-validation-candidates":
        ranking_config = load_ranking_data_config(args.ranking_config)
        version_id = args.dataset_version or ranking_config.dataset_version
        artifacts = {
            "als": AlsArtifact.load(args.als_artifact),
            "item_graph": ItemGraphArtifact.load(args.item_graph_artifact),
            "two_tower": TwoTowerArtifact.load(args.two_tower_artifact),
            "content": TfidfArtifact.load(args.content_artifact),
        }
        with tracked_run(
            load_tracking_config(args.tracking_config),
            stage="ranking_validation_candidates",
            dataset_version=version_id,
            experiment_name=ranking_config.mlflow_experiment_name,
        ) as run:
            result = build_validation_candidates(
                config.dataset.versions_dir / version_id,
                ranking_config,
                artifacts,
            )
            run.log_params(
                {
                    "ranking_config_sha256": result.manifest["ranking_config_sha256"],
                    "candidate_k_per_source": str(
                        result.manifest["candidate_k_per_source"]
                    ),
                }
            )
            run.log_counts(
                {
                    key: value
                    for key, value in result.manifest.items()
                    if isinstance(value, int)
                }
            )
            run.log_manifest(result.output_dir / "manifest.json")
            print(json.dumps(result.manifest, indent=2, sort_keys=True))
        return
    if args.command == "ranking-test-candidates":
        ranking_config = load_ranking_data_config(args.ranking_config)
        version_id = args.dataset_version or ranking_config.dataset_version
        artifacts = {
            "als": AlsArtifact.load(args.als_artifact),
            "item_graph": ItemGraphArtifact.load(args.item_graph_artifact),
            "two_tower": TwoTowerArtifact.load(args.two_tower_artifact),
            "content": TfidfArtifact.load(args.content_artifact),
        }
        with tracked_run(
            load_tracking_config(args.tracking_config),
            stage="ranking_test_candidates",
            dataset_version=version_id,
            experiment_name=ranking_config.mlflow_experiment_name,
        ) as run:
            result = build_test_candidates(
                config.dataset.versions_dir / version_id, ranking_config, artifacts
            )
            run.log_params(
                {
                    "ranking_config_sha256": result.manifest["ranking_config_sha256"],
                    "candidate_k_per_source": str(
                        result.manifest["candidate_k_per_source"]
                    ),
                }
            )
            run.log_counts(
                {
                    key: value
                    for key, value in result.manifest.items()
                    if isinstance(value, int)
                }
            )
            run.log_manifest(result.output_dir / "manifest.json")
            print(json.dumps(result.manifest, indent=2, sort_keys=True))
        return
    version_id = _resolve_version(config, args.dataset_version, complete=True)
    manifest = validate_dataset(config.dataset.versions_dir / version_id)
    if args.command == "status":
        print(
            json.dumps(
                {"version_id": version_id, "status": manifest["status"]}, indent=2
            )
        )
        return
    with tracked_run(
        load_tracking_config(args.tracking_config),
        stage="validate",
        dataset_version=version_id,
    ) as run:
        run.log_counts(
            {key: value for key, value in manifest.items() if isinstance(value, int)}
        )
        run.log_manifest(config.dataset.versions_dir / version_id / "manifest.json")
        print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
