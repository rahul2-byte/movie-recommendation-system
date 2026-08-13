"""Train and validate reproducible local retrieval artifacts."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pyarrow.parquet as pq
from data_pipeline.config import load_config as load_data_config
from data_pipeline.manifests import sha256
from data_pipeline.tracking import load_tracking_config, tracked_run
from data_pipeline.validate import validate_dataset
from evaluation.config import load_evaluation_config
from evaluation.runner import evaluate_recommender, write_evaluation_artifacts

from training.progress import TerminalProgress
from training.retrieval.build_als import load_als_training_config, train_als
from training.retrieval.build_content_retriever import (
    build_exact_seed_cache,
    load_content_training_config,
    load_tfidf_training_config,
    train_tfidf,
)
from training.retrieval.build_item_graph import (
    build_item_graph_seed_cache,
    load_item_graph_training_config,
    train_item_graph,
)
from training.retrieval.build_two_tower import (
    load_two_tower_training_config,
    train_two_tower,
)


def _default_config(name: str) -> Path:
    """Return the default retrieval config path."""
    return Path(__file__).resolve().parent.parent.parent / "configs" / name


def _run_id() -> str:
    """Create a UTC run identifier for retrieval artifacts."""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _git_sha() -> str | None:
    """Return the current Git revision when available."""
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _metric_values(summary: dict[str, object]) -> dict[str, float]:
    """Flatten evaluation metrics for telemetry logging."""
    metrics = {
        "query_count": float(summary["query_count"]),
        "failures": float(summary["failures"]),
    }
    for k, values in summary["metrics"].items():
        for name, value in values.items():
            metrics[f"{name}_{k}"] = float(value)
    return metrics


def _resolve_train_path(version_dir: Path, explicit_path: Path | None) -> Path:
    """Return an explicit immutable training input or the canonical train split."""
    train_path = (explicit_path or version_dir / "train.parquet").resolve()
    if not train_path.is_file():
        raise FileNotFoundError(f"Retrieval training data not found: {train_path}")
    return train_path


def _resolve_content_lineage_path(
    version_dir: Path, explicit_path: Path | None
) -> Path:
    """Use interaction history as content-artifact lineage, not model input."""
    return _resolve_train_path(version_dir, explicit_path)


def main() -> None:
    """Dispatch canonical retrieval training and optional evaluation."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "model", choices=("tfidf", "content", "als", "two_tower", "item_graph")
    )
    parser.add_argument(
        "--config", type=Path, default=_default_config("retrieval_training.yaml")
    )
    parser.add_argument(
        "--data-config", type=Path, default=_default_config("data_pipeline.yaml")
    )
    parser.add_argument(
        "--evaluation-config", type=Path, default=_default_config("evaluation.yaml")
    )
    parser.add_argument(
        "--tracking-config", type=Path, default=_default_config("mlflow.yaml")
    )
    parser.add_argument(
        "--ci", action="store_true", help="Evaluate the deterministic CI query subset"
    )
    parser.add_argument(
        "--train-path",
        type=Path,
        help="Immutable Parquet interactions to fit instead of <dataset>/train.parquet",
    )
    parser.add_argument(
        "--skip-evaluation",
        action="store_true",
        help="Train and track an artifact without reading validation queries",
    )
    args = parser.parse_args()
    model_type = args.model
    loaders = {
        "tfidf": load_tfidf_training_config,
        "content": load_content_training_config,
        "als": load_als_training_config,
        "two_tower": load_two_tower_training_config,
        "item_graph": load_item_graph_training_config,
    }
    training_config = loaders[model_type](args.config)
    data_config = load_data_config(args.data_config)
    evaluation_config = load_evaluation_config(args.evaluation_config)
    version_dir = data_config.dataset.versions_dir / training_config.dataset_version
    validate_dataset(version_dir)
    if model_type == "tfidf" and args.train_path is not None:
        parser.error("--train-path is not supported by the standalone tfidf retriever")
    train_path = _resolve_train_path(version_dir, args.train_path)
    catalog_path = version_dir / "catalog.parquet"
    if model_type == "tfidf":
        train_path = catalog_path
    elif model_type == "content":
        train_path = _resolve_content_lineage_path(version_dir, args.train_path)
    if not catalog_path.is_file():
        raise FileNotFoundError(f"Retrieval catalog not found: {catalog_path}")
    run_id = _run_id()
    artifact_dir = training_config.output_dir / run_id
    metadata = {
        "training_config_sha256": sha256(args.config),
        "dataset_manifest_sha256": sha256(version_dir / "manifest.json"),
        "training_data_path": str(train_path),
        "training_data_sha256": sha256(train_path),
        "train_sha256": sha256(train_path),
        "per_seed_candidates": training_config.per_seed_candidates,
        "git_sha": _git_sha(),
        "command": " ".join(sys.argv),
    }
    if model_type in {"tfidf", "content"}:
        training_progress = TerminalProgress(f"{model_type} training", total=6)
        artifact = train_tfidf(
            catalog_path,
            artifact_dir,
            text_fields=training_config.text_fields,
            field_weights=training_config.field_weights,
            min_df=training_config.min_df,
            max_features=training_config.max_features,
            embedding_dim=training_config.embedding_dim,
            random_seed=training_config.random_seed,
            dataset_version=training_config.dataset_version,
            model_type=model_type,
            training_metadata=metadata,
            progress_callback=training_progress.update,
        )
    elif model_type == "als":
        training_progress = TerminalProgress("als training", total=5)
        artifact = train_als(
            train_path,
            artifact_dir,
            factors=training_config.factors,
            regularization=training_config.regularization,
            alpha=training_config.alpha,
            iterations=training_config.iterations,
            num_threads=training_config.num_threads,
            random_seed=training_config.random_seed,
            dataset_version=training_config.dataset_version,
            per_seed_candidates=training_config.per_seed_candidates,
            parquet_batch_size=training_config.parquet_batch_size,
            training_metadata=metadata,
            progress_callback=training_progress.update,
        )
    elif model_type == "two_tower":
        training_progress = TerminalProgress(
            "two_tower training", total=5 + training_config.epochs
        )
        artifact = train_two_tower(
            train_path,
            artifact_dir,
            embedding_dim=training_config.embedding_dim,
            batch_size=training_config.batch_size,
            epochs=training_config.epochs,
            learning_rate=training_config.learning_rate,
            max_pairs_per_user=training_config.max_pairs_per_user,
            random_seed=training_config.random_seed,
            dataset_version=training_config.dataset_version,
            per_seed_candidates=training_config.per_seed_candidates,
            training_metadata=metadata,
            progress_callback=training_progress.update,
        )
    else:
        training_progress = TerminalProgress("item_graph training", total=6)
        artifact = train_item_graph(
            train_path,
            artifact_dir,
            neighbor_count=training_config.neighbor_count,
            k1=training_config.k1,
            b=training_config.b,
            num_threads=training_config.num_threads,
            random_seed=training_config.random_seed,
            dataset_version=training_config.dataset_version,
            per_seed_candidates=training_config.per_seed_candidates,
            parquet_batch_size=training_config.parquet_batch_size,
            training_metadata=metadata,
            progress_callback=training_progress.update,
        )
    if args.skip_evaluation:
        with tracked_run(
            load_tracking_config(args.tracking_config),
            stage=f"train_{model_type}",
            dataset_version=training_config.dataset_version,
            experiment_name=training_config.mlflow_experiment_name,
        ) as run:
            run.log_params({key: str(value) for key, value in metadata.items()})
            run.log_artifact(
                artifact.output_dir / "manifest.json", artifact_path="model"
            )
            run.log_manifest(version_dir / "manifest.json")
        print(
            json.dumps(
                {
                    "artifact_dir": str(artifact.output_dir),
                    "dataset_version": training_config.dataset_version,
                    "model_type": model_type,
                    "training_data_path": str(train_path),
                    "validation": "skipped",
                },
                indent=2,
                sort_keys=True,
            )
        )
        return
    query_limit = evaluation_config.ci_query_limit if args.ci else None
    cache_progress: TerminalProgress | None = None

    def report_cache(completed: int, total: int) -> None:
        """Render seed-cache progress on stderr."""
        nonlocal cache_progress
        if total == 0:
            return
        if cache_progress is None:
            cache_progress = TerminalProgress(f"{model_type} seed cache", total=total)
        cache_progress.update(completed, f"{total} unique seeds")

    cache_builder = (
        build_item_graph_seed_cache
        if model_type == "item_graph"
        else build_exact_seed_cache
    )
    cached_recommender = cache_builder(
        artifact,
        version_dir / "validation.parquet",
        query_limit=query_limit,
        batch_size=evaluation_config.tfidf_seed_cache_batch_size,
        progress_callback=report_cache,
    )
    validation_rows = pq.ParquetFile(
        version_dir / "validation.parquet"
    ).metadata.num_rows
    evaluation_progress = TerminalProgress(
        f"{model_type} validation",
        total=min(validation_rows, query_limit) if query_limit else validation_rows,
    )
    summary = evaluate_recommender(
        cached_recommender,
        version_dir / "validation.parquet",
        catalog_size=pq.ParquetFile(version_dir / "catalog.parquet").metadata.num_rows,
        k_values=evaluation_config.k_values,
        query_limit=query_limit,
        progress_callback=evaluation_progress.update,
    )
    summary.update(
        {
            "model_type": model_type,
            "dataset_version": training_config.dataset_version,
            "artifact_dir": str(artifact.output_dir),
            "partition": "validation",
            "exact_seed_cache_batch_size": evaluation_config.tfidf_seed_cache_batch_size,
            "exact_seed_cache_entries": len(cached_recommender.row_by_seed),
        }
    )
    evaluation_dir = evaluation_config.output_dir / run_id
    run_config: dict[str, object] = {
        "model_type": model_type,
        "dataset_version": training_config.dataset_version,
        "artifact_dir": str(artifact.output_dir),
        "training_config_sha256": sha256(args.config),
        "evaluation_config_sha256": sha256(args.evaluation_config),
        "dataset_manifest_sha256": sha256(version_dir / "manifest.json"),
        "query_limit": query_limit,
        "exact_seed_cache_batch_size": evaluation_config.tfidf_seed_cache_batch_size,
        "exact_seed_cache_entries": len(cached_recommender.row_by_seed),
        "command": " ".join(sys.argv),
    }
    write_evaluation_artifacts(evaluation_dir, run_config, summary)
    with tracked_run(
        load_tracking_config(args.tracking_config),
        stage=f"train_{model_type}",
        dataset_version=training_config.dataset_version,
        experiment_name=training_config.mlflow_experiment_name,
    ) as run:
        run.log_params({key: str(value) for key, value in run_config.items()})
        run.log_metrics(_metric_values(summary))
        run.log_artifact(artifact.output_dir / "manifest.json", artifact_path="model")
        run.log_artifact(evaluation_dir / "summary.json", artifact_path="evaluation")
        run.log_manifest(version_dir / "manifest.json")
    print(
        json.dumps(
            {
                "artifact_dir": str(artifact.output_dir),
                "evaluation_dir": str(evaluation_dir),
                **summary,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
