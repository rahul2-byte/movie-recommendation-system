"""Train and compare graph/content compression variants outside source control."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from serving.bundle_recommender import BundleRecommender


def _bytes(root: Path) -> int:
    """Return the total payload size for one artifact or bundle."""
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file())


def _component_bytes(root: Path) -> dict[str, int]:
    """Return sizes grouped by serving bundle component."""
    return {
        path.relative_to(root).as_posix(): _bytes(path)
        for path in sorted(root.glob("retrievers/*")) + [root / "ranker"]
        if path.is_dir()
    }


def _train(
    model: str,
    artifact_dir: Path,
    *,
    config: Path,
    data_config: Path,
    tracking_config: Path,
    embedding_dim: int | None = None,
    neighbor_count: int | None = None,
) -> Path:
    """Run the canonical trainer with an exact, immutable output directory."""
    command = [
        sys.executable,
        "-m",
        "training.retrieval.cli",
        model,
        "--config",
        str(config),
        "--data-config",
        str(data_config),
        "--tracking-config",
        str(tracking_config),
        "--artifact-dir",
        str(artifact_dir),
        "--skip-evaluation",
    ]
    if embedding_dim is not None:
        command.extend(("--embedding-dim", str(embedding_dim)))
    if neighbor_count is not None:
        command.extend(("--neighbor-count", str(neighbor_count)))
    completed = subprocess.run(command, check=False, text=True, capture_output=True)
    if completed.returncode:
        raise RuntimeError(
            f"{model} training failed:\n{completed.stdout}\n{completed.stderr}"
        )
    result = json.loads(completed.stdout)
    trained_path = Path(result["artifact_dir"]).resolve()
    if (
        trained_path != artifact_dir.resolve()
        or not (trained_path / "manifest.json").is_file()
    ):
        raise RuntimeError(f"Trainer returned an invalid artifact path: {trained_path}")
    return trained_path


def _build_bundle(
    output_dir: Path,
    sources: dict[str, Path],
    popularity_train_path: Path,
    quantization: str,
) -> Path:
    """Build one immutable serving bundle from the selected model variants."""
    from serving.model_bundle import build_model_bundle

    return build_model_bundle(
        sources,
        output_dir,
        popularity_train_path=popularity_train_path,
        quantization=quantization,
    )


def _overlap(
    reference: Path, candidate: Path, seeds: list[int], limits: list[int]
) -> dict[str, Any]:
    """Compare deterministic recommendation overlap against the baseline."""
    reference_recommender = BundleRecommender.load(reference)
    candidate_recommender = BundleRecommender.load(candidate)
    result: dict[str, Any] = {}
    for limit in limits:
        reference_ids = {
            item_id
            for item_id, _ in reference_recommender.recommend(seeds, {}, top_n=limit)
        }
        candidate_ids = {
            item_id
            for item_id, _ in candidate_recommender.recommend(seeds, {}, top_n=limit)
        }
        union = reference_ids | candidate_ids
        result[str(limit)] = {
            "overlap": len(reference_ids & candidate_ids),
            "jaccard": len(reference_ids & candidate_ids) / len(union)
            if union
            else 1.0,
            "reference_count": len(reference_ids),
            "candidate_count": len(candidate_ids),
        }
    return result


def main() -> None:
    """Execute the full graph-depth/content-dimension/quantization sweep."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--data-config", type=Path, required=True)
    parser.add_argument("--tracking-config", type=Path, required=True)
    parser.add_argument("--popularity-train-path", type=Path, required=True)
    parser.add_argument("--als-artifact", type=Path, required=True)
    parser.add_argument("--two-tower-artifact", type=Path, required=True)
    parser.add_argument("--ranker-artifact", type=Path, required=True)
    parser.add_argument("--reference-bundle", type=Path)
    parser.add_argument("--seed-tmdb-ids", type=int, nargs="*")
    parser.add_argument(
        "--graph-depths", type=int, nargs="+", default=[25, 50, 100, 150, 200, 300]
    )
    parser.add_argument(
        "--content-dims", type=int, nargs="+", default=[32, 64, 128, 256, 384]
    )
    parser.add_argument(
        "--quantizations", nargs="+", default=["none", "fp16", "int8", "sq6", "sq4"]
    )
    args = parser.parse_args()
    if any(value < 1 for value in (*args.graph_depths, *args.content_dims)):
        parser.error("graph depths and content dimensions must be positive")
    output_root = args.output_root.resolve()
    artifacts_root = output_root / "artifacts"
    bundles_root = output_root / "bundles"
    artifacts_root.mkdir(parents=True, exist_ok=True)
    bundles_root.mkdir(parents=True, exist_ok=True)

    graph_artifacts = {
        depth: _train(
            "item_graph",
            artifacts_root / f"graph-{depth}",
            config=args.config.resolve(),
            data_config=args.data_config.resolve(),
            tracking_config=args.tracking_config.resolve(),
            neighbor_count=depth,
        )
        for depth in args.graph_depths
    }
    content_artifacts = {
        dimension: _train(
            "content",
            artifacts_root / f"content-{dimension}",
            config=args.config.resolve(),
            data_config=args.data_config.resolve(),
            tracking_config=args.tracking_config.resolve(),
            embedding_dim=dimension,
        )
        for dimension in args.content_dims
    }
    fixed_sources = {
        "als": args.als_artifact.resolve(),
        "two_tower": args.two_tower_artifact.resolve(),
        "ranker": args.ranker_artifact.resolve(),
    }
    reference = args.reference_bundle.resolve() if args.reference_bundle else None
    limits = [100, 200, 300]
    results: list[dict[str, Any]] = []
    for depth, graph_artifact in graph_artifacts.items():
        for dimension, content_artifact in content_artifacts.items():
            for quantization in args.quantizations:
                bundle_dir = (
                    bundles_root / f"graph-{depth}-content-{dimension}-{quantization}"
                )
                started = time.perf_counter()
                _build_bundle(
                    bundle_dir,
                    {
                        **fixed_sources,
                        "item_graph": graph_artifact,
                        "content": content_artifact,
                    },
                    args.popularity_train_path.resolve(),
                    quantization,
                )
                result: dict[str, Any] = {
                    "graph_depth": depth,
                    "content_dimension": dimension,
                    "quantization": quantization,
                    "bundle": str(bundle_dir),
                    "bundle_bytes": _bytes(bundle_dir),
                    "component_bytes": _component_bytes(bundle_dir),
                    "build_seconds": time.perf_counter() - started,
                }
                if reference and args.seed_tmdb_ids:
                    result["overlap_vs_reference"] = _overlap(
                        reference, bundle_dir, args.seed_tmdb_ids, limits
                    )
                results.append(result)
                print(json.dumps(result, sort_keys=True), flush=True)
    summary = output_root / "compression-sweep.json"
    summary.write_text(
        json.dumps(
            {
                "schema_version": "compression-sweep-v1",
                "graph_depths": args.graph_depths,
                "content_dimensions": args.content_dims,
                "quantizations": args.quantizations,
                "results": results,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"summary": str(summary), "result_count": len(results)}))


if __name__ == "__main__":
    main()
