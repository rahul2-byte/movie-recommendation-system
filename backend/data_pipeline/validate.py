"""Validation for finalized immutable dataset versions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from data_pipeline.manifests import sha256


def _validate_query_boundaries(path: Path) -> None:
    columns = [
        "query_id",
        "seed_tmdb_ids",
        "ground_truth_tmdb_ids",
        "history_end_timestamp",
        "ground_truth_start_timestamp",
    ]
    queries = pd.read_parquet(path, columns=columns)
    if queries.empty:
        raise ValueError(f"Query output is empty: {path}")
    invalid = (
        queries["history_end_timestamp"] >= queries["ground_truth_start_timestamp"]
    )
    if invalid.any():
        query_id = queries.loc[invalid, "query_id"].iloc[0]
        raise ValueError(f"Query target must be strictly after history: {query_id}")
    if queries["seed_tmdb_ids"].map(len).eq(0).any():
        raise ValueError(f"Query output contains empty seed IDs: {path}")
    if queries["ground_truth_tmdb_ids"].map(len).eq(0).any():
        raise ValueError(f"Query output contains empty ground-truth IDs: {path}")


def validate_dataset(version_dir: Path) -> dict[str, Any]:
    manifest_path = version_dir / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Dataset manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "complete":
        raise ValueError(f"Dataset version is not complete: {version_dir.name}")
    expected = manifest.get("output_sha256")
    if not isinstance(expected, dict):
        raise ValueError("Dataset manifest is missing output_sha256")
    for name in ("catalog", "train", "validation", "test"):
        path = version_dir / f"{name}.parquet"
        if not path.is_file():
            raise FileNotFoundError(f"Dataset output missing: {path}")
        if expected.get(name) != sha256(path):
            raise ValueError(f"Dataset output hash mismatch: {path}")
    for name in ("validation", "test"):
        _validate_query_boundaries(version_dir / f"{name}.parquet")
    return manifest
