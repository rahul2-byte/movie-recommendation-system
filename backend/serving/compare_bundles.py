"""Compare two immutable bundles on identical local recommendation inputs."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from serving.bundle_recommender import BundleRecommender


def _bundle_bytes(root: Path) -> int:
    """Return the payload size of one bundle in bytes."""
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file())


def _recommend(
    root: Path, seed_ids: list[int], limit: int
) -> tuple[float, list[int], dict]:
    """Load a bundle and produce one deterministic recommendation list."""
    started = time.perf_counter()
    recommender = BundleRecommender.load(root)
    load_ms = (time.perf_counter() - started) * 1_000
    recommendations = recommender.recommend(seed_ids, {}, top_n=limit)
    return (
        load_ms,
        [item_id for item_id, _ in recommendations],
        recommender.bundle.manifest,
    )


def main() -> None:
    """Print size, startup, and recommendation-overlap comparisons."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference-bundle", type=Path, required=True)
    parser.add_argument("--candidate-bundle", type=Path, required=True)
    parser.add_argument("--seed-tmdb-ids", type=int, nargs="+", required=True)
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    if not args.seed_tmdb_ids or args.limit < 1:
        parser.error("seed IDs and limit must be positive")

    reference_load_ms, reference_ids, reference_manifest = _recommend(
        args.reference_bundle.resolve(), args.seed_tmdb_ids, args.limit
    )
    candidate_load_ms, candidate_ids, candidate_manifest = _recommend(
        args.candidate_bundle.resolve(), args.seed_tmdb_ids, args.limit
    )
    reference_set = set(reference_ids)
    candidate_set = set(candidate_ids)
    union = reference_set | candidate_set
    report = {
        "schema_version": "bundle-comparison-v1",
        "reference": {
            "path": str(args.reference_bundle.resolve()),
            "bytes": _bundle_bytes(args.reference_bundle.resolve()),
            "load_ms": reference_load_ms,
            "quantization": reference_manifest.get("quantization", "none"),
        },
        "candidate": {
            "path": str(args.candidate_bundle.resolve()),
            "bytes": _bundle_bytes(args.candidate_bundle.resolve()),
            "load_ms": candidate_load_ms,
            "quantization": candidate_manifest.get("quantization", "none"),
        },
        "seed_tmdb_ids": args.seed_tmdb_ids,
        "limit": args.limit,
        "recommendation_overlap_count": len(reference_set & candidate_set),
        "recommendation_jaccard": (
            len(reference_set & candidate_set) / len(union) if union else 1.0
        ),
        "reference_recommendations": reference_ids,
        "candidate_recommendations": candidate_ids,
    }
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
