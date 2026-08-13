"""Streaming offline evaluation and evidence artifact writing."""

from __future__ import annotations

import json
import platform
import subprocess
import time
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Protocol

import numpy as np
import pyarrow.parquet as pq

from evaluation.metrics import ranking_metrics, sanitize_recommendations


class Recommender(Protocol):
    def recommend(self, seed_tmdb_ids: list[int], top_k: int) -> list[int]: ...


def _latency_summary(samples_ms: list[float]) -> dict[str, float]:
    values = np.asarray(samples_ms, dtype=np.float64)
    return {
        "mean": float(values.mean()),
        "max": float(values.max()),
        "p50": float(np.percentile(values, 50)),
        "p95": float(np.percentile(values, 95)),
        "p99": float(np.percentile(values, 99)),
    }


def evaluate_recommender(
    recommender: Recommender,
    queries_path: Path,
    *,
    catalog_size: int,
    k_values: Iterable[int],
    query_limit: int | None = None,
    progress_callback: Callable[[int, int], None] | None = None,
) -> dict[str, object]:
    """Evaluate one recommender against query records without loading all queries."""
    k_values = tuple(sorted(set(int(k) for k in k_values)))
    if not k_values or k_values[0] < 1:
        raise ValueError("k_values must contain positive integers")
    if catalog_size < 1:
        raise ValueError("catalog_size must be positive")
    if query_limit is not None and query_limit < 1:
        raise ValueError("query_limit must be positive when provided")
    columns = ["query_id", "seed_tmdb_ids", "ground_truth_tmdb_ids"]
    source = pq.ParquetFile(queries_path)
    missing = set(columns) - set(source.schema_arrow.names)
    if missing:
        raise ValueError(f"Query data is missing columns: {sorted(missing)}")
    totals = {k: {"recall": 0.0, "hit_rate": 0.0, "precision": 0.0} for k in k_values}
    catalog_ids = {k: set() for k in k_values}
    user_coverage = {k: 0 for k in k_values}
    latencies_ms: list[float] = []
    query_count = failures = 0
    max_k = max(k_values)
    total_queries = (
        min(source.metadata.num_rows, query_limit)
        if query_limit
        else source.metadata.num_rows
    )
    for batch in source.iter_batches(columns=columns, batch_size=5_000):
        for query in batch.to_pylist():
            if query_limit is not None and query_count == query_limit:
                break
            query_count += 1
            seeds = [int(item_id) for item_id in query["seed_tmdb_ids"]]
            relevant = {int(item_id) for item_id in query["ground_truth_tmdb_ids"]}
            started = time.perf_counter()
            try:
                predicted = sanitize_recommendations(
                    recommender.recommend(seeds, max_k), set(seeds), max_k
                )
            except Exception:
                failures += 1
                predicted = []
            finally:
                latencies_ms.append((time.perf_counter() - started) * 1_000)
            for k in k_values:
                metrics = ranking_metrics(predicted, relevant, k)
                for name, value in metrics.items():
                    totals[k][name] += value
                catalog_ids[k].update(predicted[:k])
                user_coverage[k] += int(bool(predicted[:k]))
        if progress_callback is not None:
            progress_callback(query_count, total_queries)
        if query_limit is not None and query_count == query_limit:
            break
    if not query_count:
        raise ValueError(f"No queries evaluated from {queries_path}")
    if progress_callback is not None and query_count != total_queries:
        progress_callback(query_count, total_queries)
    return {
        "query_count": query_count,
        "failures": failures,
        "latency_ms": _latency_summary(latencies_ms),
        "metrics": {
            str(k): {
                "recall_at_k": totals[k]["recall"] / query_count,
                "hit_rate_at_k": totals[k]["hit_rate"] / query_count,
                "precision_at_k": totals[k]["precision"] / query_count,
                "catalog_coverage_at_k": len(catalog_ids[k]) / catalog_size,
                "user_coverage_at_k": user_coverage[k] / query_count,
            }
            for k in k_values
        },
    }


def _write_json(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def _git_sha() -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False
    )
    return result.stdout.strip() if result.returncode == 0 else None


def write_evaluation_artifacts(
    output_dir: Path, config: dict[str, object], summary: dict[str, object]
) -> None:
    """Atomically persist the minimum reproducibility evidence for one run."""
    _write_json(output_dir / "config.json", config)
    _write_json(
        output_dir / "environment.json",
        {"git_sha": _git_sha(), "python": platform.python_version()},
    )
    _write_json(output_dir / "summary.json", summary)
    _write_json(output_dir / "retrieval_metrics.json", summary)
