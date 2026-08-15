"""Run reproducible offline recommendation evaluations."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pyarrow.parquet as pq
from data_pipeline.config import load_config as load_data_config
from data_pipeline.tracking import load_tracking_config, tracked_run
from data_pipeline.validate import validate_dataset
from hashing import sha256
from training.progress import TerminalProgress
from training.retrieval.als_trainer import AlsArtifact
from training.retrieval.content_retriever import build_exact_seed_cache
from training.retrieval.item_graph_trainer import (
    ItemGraphArtifact,
    build_item_graph_seed_cache,
)
from training.retrieval.two_tower_trainer import TwoTowerArtifact

from evaluation.baselines import PopularityRecommender
from evaluation.config import load_evaluation_config
from evaluation.offline_evaluator import (
    evaluate_recommender,
    write_evaluation_artifacts,
)
from evaluation.rank_fusion import RankFusionRecommender, analyze_candidate_overlap


def _default_config(name: str) -> Path:
    """Return the repository default evaluation config path."""
    return Path(__file__).resolve().parent.parent / "configuration" / name


def _run_id() -> str:
    """Create a UTC identifier for one evaluation report."""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _metric_values(summary: dict[str, object]) -> dict[str, float]:
    """Extract scalar metrics from a nested evaluation summary."""
    result = {
        "query_count": float(summary["query_count"]),
        "failures": float(summary["failures"]),
    }
    for k, metrics in summary["metrics"].items():
        for name, value in metrics.items():
            result[f"{name}_{k}"] = float(value)
    for name, value in summary["latency_ms"].items():
        result[f"latency_ms_{name}"] = float(value)
    return result


def main() -> None:
    """Run configured offline evaluation and write its immutable report."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path, default=_default_config("evaluation.yaml")
    )
    parser.add_argument(
        "--data-config", type=Path, default=_default_config("data_pipeline.yaml")
    )
    parser.add_argument(
        "--tracking-config", type=Path, default=_default_config("mlflow.yaml")
    )
    parser.add_argument("--dataset-version")
    parser.add_argument(
        "--partition", choices=("validation", "test"), default="validation"
    )
    parser.add_argument(
        "--ci", action="store_true", help="Use the deterministic CI query limit"
    )
    parser.add_argument("--final-evaluation", action="store_true")
    parser.add_argument(
        "baseline", choices=("popularity", "als-two-tower", "als-item-graph")
    )
    parser.add_argument("--als-artifact", type=Path)
    parser.add_argument("--two-tower-artifact", type=Path)
    parser.add_argument("--item-graph-artifact", type=Path)
    args = parser.parse_args()
    if args.partition == "test" and not args.final_evaluation:
        parser.error("test evaluation requires --final-evaluation")
    evaluation_config = load_evaluation_config(args.config)
    data_config = load_data_config(args.data_config)
    version_id = args.dataset_version or evaluation_config.dataset_version
    version_dir = data_config.dataset.versions_dir / version_id
    validate_dataset(version_dir)
    query_limit = evaluation_config.ci_query_limit if args.ci else None
    run_config: dict[str, object] = {
        "baseline": args.baseline,
        "dataset_version": version_id,
        "dataset_manifest_sha256": sha256(version_dir / "manifest.json"),
        "evaluation_config_sha256": sha256(args.config),
        "partition": args.partition,
        "k_values": list(evaluation_config.k_values),
        "query_limit": query_limit,
        "command": " ".join(__import__("sys").argv),
    }
    queries_path = version_dir / f"{args.partition}.parquet"
    catalog_size = pq.ParquetFile(version_dir / "catalog.parquet").metadata.num_rows
    if args.baseline == "popularity":
        recommender = PopularityRecommender.fit(version_dir / "train.parquet")
        summary = evaluate_recommender(
            recommender,
            queries_path,
            catalog_size=catalog_size,
            k_values=evaluation_config.k_values,
            query_limit=query_limit,
        )
    else:
        if args.als_artifact is None:
            parser.error(f"{args.baseline} requires --als-artifact")
        als_artifact = AlsArtifact.load(args.als_artifact)
        if args.baseline == "als-two-tower":
            if args.two_tower_artifact is None:
                parser.error("als-two-tower requires --two-tower-artifact")
            secondary_name = "two_tower"
            secondary_artifact = TwoTowerArtifact.load(args.two_tower_artifact)
            secondary_cache_builder = build_exact_seed_cache
        else:
            if args.item_graph_artifact is None:
                parser.error("als-item-graph requires --item-graph-artifact")
            secondary_name = "item_graph"
            secondary_artifact = ItemGraphArtifact.load(args.item_graph_artifact)
            secondary_cache_builder = build_item_graph_seed_cache
        for name, artifact in (
            ("als", als_artifact),
            (secondary_name, secondary_artifact),
        ):
            if artifact.manifest.get("dataset_version") != version_id:
                parser.error(
                    f"{name} artifact dataset version does not match {version_id}"
                )

        def cache(artifact, name: str, cache_builder):
            """Build and report progress for one retriever's seed cache."""
            progress: TerminalProgress | None = None

            def report(completed: int, total: int) -> None:
                """Render cache progress after the first batch reveals total work."""
                nonlocal progress
                if total and progress is None:
                    progress = TerminalProgress(f"{name} seed cache", total)
                if progress is not None:
                    progress.update(completed, f"{total} unique seeds")

            return cache_builder(
                artifact,
                queries_path,
                query_limit=query_limit,
                batch_size=evaluation_config.tfidf_seed_cache_batch_size,
                progress_callback=report,
            )

        als = cache(als_artifact, "als", build_exact_seed_cache)
        secondary = cache(secondary_artifact, secondary_name, secondary_cache_builder)
        recommenders = {"als": als, secondary_name: secondary}
        fusion = RankFusionRecommender(
            recommenders,
            rank_constant=evaluation_config.rrf_rank_constant,
            candidate_k=evaluation_config.fusion_candidate_k,
        )
        query_count = (
            min(pq.ParquetFile(queries_path).metadata.num_rows, query_limit)
            if query_limit
            else pq.ParquetFile(queries_path).metadata.num_rows
        )

        def evaluate(name: str, recommender):
            """Evaluate one cached recommender over the selected query partition."""
            progress = TerminalProgress(f"{name} validation", query_count)
            return evaluate_recommender(
                recommender,
                queries_path,
                catalog_size=catalog_size,
                k_values=evaluation_config.k_values,
                query_limit=query_limit,
                progress_callback=progress.update,
            )

        als_summary = evaluate("als", als)
        secondary_summary = evaluate(secondary_name, secondary)
        summary = evaluate(f"als_{secondary_name}_rrf", fusion)
        overlap_progress = TerminalProgress(
            f"als_{secondary_name} overlap", query_count
        )
        overlap = analyze_candidate_overlap(
            als,
            secondary,
            queries_path,
            candidate_k=evaluation_config.fusion_candidate_k,
            query_limit=query_limit,
            progress_callback=overlap_progress.update,
            first_name="als",
            second_name=secondary_name,
        )
        run_config.update(
            {
                "als_artifact": str(als_artifact.output_dir),
                f"{secondary_name}_artifact": str(secondary_artifact.output_dir),
                "als_manifest_sha256": sha256(
                    als_artifact.output_dir / "manifest.json"
                ),
                f"{secondary_name}_manifest_sha256": sha256(
                    secondary_artifact.output_dir / "manifest.json"
                ),
                "fusion": "reciprocal_rank_fusion",
                "fusion_candidate_k": evaluation_config.fusion_candidate_k,
                "rrf_rank_constant": evaluation_config.rrf_rank_constant,
                "exact_seed_cache_batch_size": evaluation_config.tfidf_seed_cache_batch_size,
            }
        )
        summary.update(
            {
                "component_metrics": {
                    "als": als_summary,
                    secondary_name: secondary_summary,
                },
                "candidate_overlap": overlap,
            }
        )
    summary.update(
        {
            "baseline": args.baseline,
            "partition": args.partition,
            "dataset_version": version_id,
        }
    )
    output_dir = evaluation_config.output_dir / _run_id()
    write_evaluation_artifacts(output_dir, run_config, summary)
    if args.baseline != "popularity":
        overlap_path = output_dir / "retriever_overlap.json"
        temporary = overlap_path.with_name(f".{overlap_path.name}.tmp")
        temporary.write_text(
            json.dumps(summary["candidate_overlap"], indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(overlap_path)
    with tracked_run(
        load_tracking_config(args.tracking_config),
        stage="evaluation",
        dataset_version=version_id,
        experiment_name=evaluation_config.mlflow_experiment_name,
    ) as run:
        run.log_params({key: str(value) for key, value in run_config.items()})
        run.log_metrics(_metric_values(summary))
        for filename in (
            "config.json",
            "environment.json",
            "summary.json",
            "retrieval_metrics.json",
        ):
            run.log_artifact(output_dir / filename)
        if args.baseline != "popularity":
            run.log_artifact(output_dir / "retriever_overlap.json")
        run.log_manifest(version_dir / "manifest.json")
    print(
        json.dumps({"output_dir": str(output_dir), **summary}, indent=2, sort_keys=True)
    )


if __name__ == "__main__":
    main()
