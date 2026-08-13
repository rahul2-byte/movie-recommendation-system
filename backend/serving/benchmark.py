"""Measure a released local bundle without conflating model and HTTP latency."""

from __future__ import annotations

import asyncio
import json
import sys
import time
from argparse import ArgumentParser
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

import numpy as np
from common.services.movie_store import MovieStore

from serving.recommender import BundleRecommender
from serving.smoke import validate_recommendation_response


def summarize_latencies(samples_ms: list[float]) -> dict[str, float | int]:
    if not samples_ms:
        raise ValueError("latency samples are empty")
    values = np.asarray(samples_ms, dtype=np.float64)
    return {
        "count": len(samples_ms),
        "mean": float(values.mean()),
        "p50": float(np.percentile(values, 50)),
        "p95": float(np.percentile(values, 95)),
        "p99": float(np.percentile(values, 99)),
    }


def validate_seed_metadata(
    seed_tmdb_ids: list[int], metadata: dict[int, dict[str, Any]]
) -> None:
    missing = sorted(set(seed_tmdb_ids) - set(metadata))
    if missing:
        raise ValueError(f"missing TMDB metadata for seed IDs: {missing}")


async def _seed_metadata(seed_tmdb_ids: list[int]) -> dict[int, dict[str, Any]]:
    store = MovieStore()
    try:
        movies = await store.get_many_by_tmdb_ids(seed_tmdb_ids)
        return {int(movie["tmdbId"]): movie for movie in movies}
    finally:
        await store.tmdb_client.close()


def _api_request(base_url: str, seed_tmdb_ids: list[int], limit: int) -> dict[str, Any]:
    request = Request(
        f"{base_url.rstrip('/')}/api/v1/recommend",
        data=json.dumps({"seed_tmdb_ids": seed_tmdb_ids, "limit": limit}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=30.0) as response:  # noqa: S310
        return json.load(response)


def _measure(
    name: str, request_count: int, action: Any
) -> tuple[list[float], list[str]]:
    samples_ms: list[float] = []
    errors: list[str] = []
    for index in range(request_count):
        started = time.perf_counter()
        try:
            action()
        except Exception as error:  # noqa: BLE001
            errors.append(f"{type(error).__name__}: {error}")
        else:
            samples_ms.append((time.perf_counter() - started) * 1_000)
        if (index + 1) % min(10, request_count) == 0 or index + 1 == request_count:
            print(f"[{name}] {index + 1}/{request_count}", file=sys.stderr)
    return samples_ms, errors


def _write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main() -> None:
    parser = ArgumentParser(description="Benchmark a released local model bundle.")
    parser.add_argument("--bundle-dir", type=Path, required=True)
    parser.add_argument("--base-url", default="http://localhost:8080")
    parser.add_argument("--seed-tmdb-ids", type=int, nargs="+", required=True)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--requests", type=int, default=50)
    parser.add_argument("--warmup-requests", type=int, default=5)
    parser.add_argument("--output-path", type=Path)
    args = parser.parse_args()
    if not 1 <= len(args.seed_tmdb_ids) <= 5:
        parser.error("--seed-tmdb-ids requires between one and five IDs")
    if min(args.limit, args.requests, args.warmup_requests) < 1:
        parser.error("--limit, --requests, and --warmup-requests must be positive")

    loaded_at = time.perf_counter()
    recommender = BundleRecommender.load(args.bundle_dir)
    bundle_load_ms = (time.perf_counter() - loaded_at) * 1_000
    seed_metadata = asyncio.run(_seed_metadata(args.seed_tmdb_ids))
    validate_seed_metadata(args.seed_tmdb_ids, seed_metadata)

    for _ in range(args.warmup_requests):
        recommender.recommend(args.seed_tmdb_ids, seed_metadata, top_n=args.limit)
        validate_recommendation_response(
            _api_request(args.base_url, args.seed_tmdb_ids, args.limit),
            seed_tmdb_ids=args.seed_tmdb_ids,
            limit=args.limit,
        )

    model_samples, model_errors = _measure(
        "model",
        args.requests,
        lambda: recommender.recommend(
            args.seed_tmdb_ids, seed_metadata, top_n=args.limit
        ),
    )
    http_samples, http_errors = _measure(
        "http",
        args.requests,
        lambda: validate_recommendation_response(
            _api_request(args.base_url, args.seed_tmdb_ids, args.limit),
            seed_tmdb_ids=args.seed_tmdb_ids,
            limit=args.limit,
        ),
    )
    report = {
        "schema_version": "serving-benchmark-v1",
        "status": "complete" if not model_errors and not http_errors else "failed",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "bundle_dir": str(args.bundle_dir.resolve()),
        "bundle_dataset_version": recommender.bundle.manifest["dataset_version"],
        "seed_tmdb_ids": args.seed_tmdb_ids,
        "seed_metadata_count": len(seed_metadata),
        "limit": args.limit,
        "warmup_requests": args.warmup_requests,
        "bundle_load_ms": bundle_load_ms,
        "model_warm_latency_ms": (
            summarize_latencies(model_samples) if model_samples else None
        ),
        "http_warm_cached_metadata_latency_ms": (
            summarize_latencies(http_samples) if http_samples else None
        ),
        "model_errors": model_errors,
        "http_errors": http_errors,
    }
    output_path = args.output_path or Path("backend/artifacts/benchmarks") / (
        f"serving-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.json"
    )
    _write_report(output_path, report)
    report["output_path"] = str(output_path.resolve())
    print(json.dumps(report, indent=2, sort_keys=True))
    if model_errors or http_errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
