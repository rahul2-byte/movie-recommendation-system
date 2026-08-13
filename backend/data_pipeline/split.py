"""Resumable temporal split creation from prepared interaction parts."""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from data_pipeline.config import DataPipelineConfig
from data_pipeline.manifests import sha256, write_json
from data_pipeline.prepare import _write_parquet
from data_pipeline.progress import ProgressReporter

log = logging.getLogger(__name__)
_INTERACTION_COLUMNS = ["user_id", "tmdb_id", "movielens_id", "rating", "timestamp"]


@dataclass(frozen=True)
class SplitResult:
    """Paths and manifest produced by temporal dataset splitting."""
    version_id: str
    version_dir: Path
    manifest: dict[str, Any]


def _parts_for_bucket(parts_dir: Path, bucket: int) -> list[Path]:
    """Return preparation parts belonging to one deterministic user bucket."""
    return sorted(parts_dir.glob(f"*-bucket-{bucket:03d}.parquet"))


def _bucket_events(parts_dir: Path, bucket: int) -> pd.DataFrame:
    """Load and concatenate all interaction parts for one bucket."""
    paths = _parts_for_bucket(parts_dir, bucket)
    if not paths:
        return pd.DataFrame(columns=_INTERACTION_COLUMNS)
    return pd.concat([pd.read_parquet(path) for path in paths], ignore_index=True)


def _positive_events(events: pd.DataFrame, threshold: float) -> pd.DataFrame:
    """Deduplicate item events and retain the latest positive interaction."""
    if events.empty:
        return events
    ordered = events.sort_values(["user_id", "tmdb_id", "timestamp"], kind="stable")
    latest = ordered.drop_duplicates(["user_id", "tmdb_id"], keep="last")
    return latest.loc[latest["rating"] >= threshold].sort_values(
        ["user_id", "timestamp", "tmdb_id"], kind="stable"
    )


def _next_distinct_timestamp(values: np.ndarray, fraction: float) -> int:
    """Find a later timestamp boundary that cannot split equal-time events."""
    index = int(np.ceil(fraction * (len(values) - 1)))
    values.partition(index)
    boundary = int(values[index])
    later_min: int | None = None
    for start in range(0, len(values), 1_000_000):
        chunk = values[start : start + 1_000_000]
        later = chunk[chunk > boundary]
        if later.size:
            candidate = int(later.min())
            later_min = candidate if later_min is None else min(later_min, candidate)
    if later_min is None:
        raise ValueError("Not enough distinct timestamps for temporal splitting")
    return later_min


def _cutoffs(
    parts_dir: Path, config: DataPipelineConfig, work_dir: Path
) -> tuple[int, int, int]:
    """Compute global temporal cutoffs from positive interaction timestamps."""
    counts: list[int] = []
    for bucket in range(config.prepare.user_bucket_count):
        positive = _positive_events(
            _bucket_events(parts_dir, bucket), config.split.positive_rating_threshold
        )
        counts.append(len(positive))
    total = sum(counts)
    if not total:
        raise ValueError("No positive interactions remain after deduplication")
    work_dir.mkdir(parents=True, exist_ok=True)
    timestamp_path = work_dir / "cutoff_timestamps.int64"
    values = np.memmap(timestamp_path, dtype=np.int64, mode="w+", shape=(total,))
    offset = 0
    for bucket, count in enumerate(counts):
        if not count:
            continue
        positive = _positive_events(
            _bucket_events(parts_dir, bucket), config.split.positive_rating_threshold
        )
        values[offset : offset + count] = positive["timestamp"].to_numpy(dtype=np.int64)
        offset += count
    values.flush()
    validation_start = _next_distinct_timestamp(values, config.split.train_fraction)
    test_start = _next_distinct_timestamp(
        values, config.split.train_fraction + config.split.validation_fraction
    )
    del values
    timestamp_path.unlink(missing_ok=True)
    return validation_start, test_start, total


def _positive_row_count(parts_dir: Path, config: DataPipelineConfig) -> int:
    """Count deduplicated positive rows across prepared buckets."""
    return sum(
        len(
            _positive_events(
                _bucket_events(parts_dir, bucket),
                config.split.positive_rating_threshold,
            )
        )
        for bucket in range(config.prepare.user_bucket_count)
    )


def _partition_user_events(
    user_events: pd.DataFrame,
    config: DataPipelineConfig,
    validation_start: int | None,
    test_start: int | None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Partition one user's chronological history into train/validation/test."""
    if config.split.strategy == "global_temporal_cutoffs":
        if validation_start is None or test_start is None:
            raise ValueError("Global temporal split requires timestamp cutoffs")
        return (
            user_events.loc[user_events["timestamp"] < validation_start],
            user_events.loc[
                (user_events["timestamp"] >= validation_start)
                & (user_events["timestamp"] < test_start)
            ],
            user_events.loc[user_events["timestamp"] >= test_start],
        )
    total = len(user_events)
    train_count = max(
        config.split.min_train_interactions, int(total * config.split.train_fraction)
    )
    train_count = min(train_count, total - 2)
    validation_count = max(1, int(total * config.split.validation_fraction))
    validation_count = min(validation_count, total - train_count - 1)
    timestamps = user_events["timestamp"].to_numpy()

    def boundary_after_timestamp(index: int, maximum: int) -> int:
        """Move a boundary past all events sharing the boundary timestamp."""
        index = min(index, maximum)
        boundary = int(np.searchsorted(timestamps, timestamps[index - 1], side="right"))
        if boundary <= maximum:
            return boundary
        return int(np.searchsorted(timestamps, timestamps[maximum - 1], side="left"))

    train_count = boundary_after_timestamp(train_count, total - 2)
    validation_end = boundary_after_timestamp(
        train_count + validation_count,
        total - 1,
    )
    return (
        user_events.iloc[:train_count],
        user_events.iloc[train_count:validation_end],
        user_events.iloc[validation_end:],
    )


def _records_for_bucket(
    events: pd.DataFrame,
    validation_start: int | None,
    test_start: int | None,
    config: DataPipelineConfig,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, int]]:
    """Build split records and leakage-safe query metadata for one bucket."""
    positive = _positive_events(events, config.split.positive_rating_threshold)
    train_frames: list[pd.DataFrame] = []
    validation_records: list[dict[str, Any]] = []
    test_records: list[dict[str, Any]] = []
    excluded = 0
    for user_id, user_events in positive.groupby("user_id", sort=False):
        if len(user_events) < config.split.min_positive_interactions:
            excluded += 1
            continue
        train, validation, test = _partition_user_events(
            user_events, config, validation_start, test_start
        )
        if (
            len(train) + len(validation) + len(test)
            < config.split.min_positive_interactions
            or len(train) < config.split.min_train_interactions
            or validation.empty
            or test.empty
        ):
            excluded += 1
            continue
        train_frames.append(train[_INTERACTION_COLUMNS])
        train_ids = train["tmdb_id"].astype(int).tolist()
        history = pd.concat([train, validation], ignore_index=True).sort_values(
            ["timestamp", "tmdb_id"], kind="stable"
        )
        validation_records.append(
            {
                "query_id": f"validation:{int(user_id)}",
                "user_id": int(user_id),
                "seed_tmdb_ids": train_ids[-config.split.seed_count :],
                "ground_truth_tmdb_ids": validation["tmdb_id"].astype(int).tolist(),
                "history_end_timestamp": int(train["timestamp"].max()),
                "ground_truth_start_timestamp": int(validation["timestamp"].min()),
            }
        )
        test_records.append(
            {
                "query_id": f"test:{int(user_id)}",
                "user_id": int(user_id),
                "seed_tmdb_ids": history["tmdb_id"]
                .astype(int)
                .tolist()[-config.split.seed_count :],
                "ground_truth_tmdb_ids": test["tmdb_id"].astype(int).tolist(),
                "history_end_timestamp": int(history["timestamp"].max()),
                "ground_truth_start_timestamp": int(test["timestamp"].min()),
            }
        )
    train_output = (
        pd.concat(train_frames, ignore_index=True)
        if train_frames
        else pd.DataFrame(columns=_INTERACTION_COLUMNS)
    )
    return (
        train_output,
        pd.DataFrame(validation_records),
        pd.DataFrame(test_records),
        {"eligible_users": len(validation_records), "excluded_users": excluded},
    )


def _compact(parts: Iterator[Path], destination: Path) -> int:
    """Stream parquet parts into one atomic output file."""
    paths = list(parts)
    if not paths:
        raise ValueError(f"No split output parts available for {destination.name}")
    temporary = destination.with_name(f".{destination.name}.tmp")
    writer: pq.ParquetWriter | None = None
    rows = 0
    try:
        for path in paths:
            table = pq.read_table(path)
            if writer is None:
                destination.parent.mkdir(parents=True, exist_ok=True)
                writer = pq.ParquetWriter(
                    temporary, table.schema, compression="zstd", compression_level=3
                )
            writer.write_table(table)
            rows += table.num_rows
    finally:
        if writer is not None:
            writer.close()
    if writer is None:
        raise ValueError(
            f"No readable split output parts available for {destination.name}"
        )
    temporary.replace(destination)
    return rows


def _load_state(path: Path, expected: dict[str, Any]) -> dict[str, Any]:
    """Load split progress and reject incompatible resume state."""
    if not path.is_file():
        return {
            **expected,
            "completed_buckets": [],
            "eligible_users": 0,
            "excluded_users": 0,
        }
    state = json.loads(path.read_text(encoding="utf-8"))
    for key, value in expected.items():
        if state.get(key) != value:
            raise ValueError(f"Cannot resume incompatible split state: {key}")
    return state


def split_dataset(config: DataPipelineConfig, version_id: str) -> SplitResult:
    """Create exactly train, validation, and test files for a prepared version."""
    version_dir = config.dataset.versions_dir / version_id
    prepare_manifest_path = version_dir / ".work" / "prepare" / "prepare_manifest.json"
    if not prepare_manifest_path.is_file():
        raise FileNotFoundError(f"Prepared dataset not found for version: {version_id}")
    prepare_manifest = json.loads(prepare_manifest_path.read_text(encoding="utf-8"))
    parts_dir = version_dir / ".work" / "prepare" / "interaction_parts"
    work_dir = version_dir / ".work" / "split"
    if config.split.strategy == "global_temporal_cutoffs":
        validation_start, test_start, positive_rows = _cutoffs(
            parts_dir, config, work_dir
        )
    else:
        validation_start, test_start = None, None
        positive_rows = _positive_row_count(parts_dir, config)
    expected = {
        "version_id": version_id,
        "config_sha256": sha256(config.path),
        "prepare_manifest_sha256": sha256(prepare_manifest_path),
        "split_strategy": config.split.strategy,
        "validation_start_timestamp": validation_start,
        "test_start_timestamp": test_start,
    }
    state_path = work_dir / "state.json"
    state = _load_state(state_path, expected)
    completed = set(state["completed_buckets"])
    resumed_buckets = len(completed)
    progress = ProgressReporter("split", config.prepare.user_bucket_count)
    for bucket in range(config.prepare.user_bucket_count):
        if bucket in completed:
            progress.report(bucket + 1, rows=state["eligible_users"])
            continue
        train, validation, test, counts = _records_for_bucket(
            _bucket_events(parts_dir, bucket), validation_start, test_start, config
        )
        if not train.empty:
            _write_parquet(
                train,
                work_dir / "parts" / "train" / f"bucket-{bucket:03d}.parquet",
                config,
            )
        if not validation.empty:
            _write_parquet(
                validation,
                work_dir / "parts" / "validation" / f"bucket-{bucket:03d}.parquet",
                config,
            )
        if not test.empty:
            _write_parquet(
                test,
                work_dir / "parts" / "test" / f"bucket-{bucket:03d}.parquet",
                config,
            )
        completed.add(bucket)
        state["completed_buckets"] = sorted(completed)
        state["eligible_users"] += counts["eligible_users"]
        state["excluded_users"] += counts["excluded_users"]
        write_json(state_path, state)
        progress.report(bucket + 1, rows=state["eligible_users"])
    rows = {
        "train_rows": _compact(
            (work_dir / "parts" / "train").glob("*.parquet"),
            version_dir / "train.parquet",
        ),
        "validation_rows": _compact(
            (work_dir / "parts" / "validation").glob("*.parquet"),
            version_dir / "validation.parquet",
        ),
        "test_rows": _compact(
            (work_dir / "parts" / "test").glob("*.parquet"),
            version_dir / "test.parquet",
        ),
    }
    manifest = {
        "status": "complete",
        "version_id": version_id,
        "schema_version": config.dataset.schema_version,
        "split_strategy": config.split.strategy,
        "config_sha256": expected["config_sha256"],
        "source_hashes": prepare_manifest["source_hashes"],
        "positive_rows_after_deduplication": positive_rows,
        "resumed_buckets": resumed_buckets,
        "eligible_users": state["eligible_users"],
        "excluded_users": state["excluded_users"],
        **rows,
        "output_sha256": {
            name: sha256(version_dir / f"{name}.parquet")
            for name in ("catalog", "train", "validation", "test")
        },
    }
    if validation_start is not None and test_start is not None:
        manifest["validation_start_timestamp"] = validation_start
        manifest["test_start_timestamp"] = test_start
    write_json(version_dir / "manifest.json", manifest)
    log.info(
        "etl.split.complete version_id=%s train_rows=%s", version_id, rows["train_rows"]
    )
    return SplitResult(version_id, version_dir, manifest)
