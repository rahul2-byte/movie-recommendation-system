"""Resumable raw MovieLens to TMDB-keyed interaction preparation."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from data_pipeline.config import DataPipelineConfig
from data_pipeline.manifests import (
    dataset_version_id,
    implementation_fingerprint,
    sha256,
    write_json,
)
from data_pipeline.progress import ProgressReporter

log = logging.getLogger(__name__)
_RAW_FILES = ("movies.csv", "links.csv", "ratings.csv", "tags.csv")


@dataclass(frozen=True)
class PrepareResult:
    """Paths and manifest produced by resumable dataset preparation."""
    version_id: str
    version_dir: Path
    work_dir: Path
    manifest: dict[str, Any]


def _write_parquet(frame: pd.DataFrame, path: Path, config: DataPipelineConfig) -> None:
    """Atomically write one compressed parquet part."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    frame.to_parquet(
        temporary,
        index=False,
        compression=config.prepare.compression,
        compression_level=config.prepare.compression_level,
    )
    temporary.replace(path)


def _source_hashes(config: DataPipelineConfig) -> dict[str, str]:
    """Hash every raw/enriched input so versions are reproducible."""
    paths = {filename: config.dataset.raw_dir / filename for filename in _RAW_FILES}
    paths["movies_enriched.parquet"] = config.dataset.enriched_metadata_path
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing data-pipeline source files: {missing}")
    return {name: sha256(path) for name, path in paths.items()}


def _build_catalog(config: DataPipelineConfig) -> pd.DataFrame:
    """Build the one-to-one MovieLens-to-TMDB catalog used downstream."""
    links = pd.read_csv(
        config.dataset.raw_dir / "links.csv", usecols=["movieId", "tmdbId"]
    )
    enriched = pd.read_parquet(config.dataset.enriched_metadata_path)
    required = {"movie_id", "tmdb_id"}
    if missing := required - set(enriched.columns):
        raise ValueError(f"Enriched metadata missing columns: {sorted(missing)}")
    mappings = links.rename(columns={"movieId": "movielens_id", "tmdbId": "tmdb_id"})
    mappings = mappings.dropna(subset=["tmdb_id"]).astype(
        {"movielens_id": "int64", "tmdb_id": "int64"}
    )
    mappings = mappings.loc[
        ~mappings["movielens_id"].duplicated(keep=False)
        & ~mappings["tmdb_id"].duplicated(keep=False)
    ]
    metadata = enriched.rename(columns={"movie_id": "movielens_id"}).copy()
    metadata = metadata.dropna(subset=["tmdb_id"])
    metadata["movielens_id"] = metadata["movielens_id"].astype("int64")
    metadata["tmdb_id"] = metadata["tmdb_id"].astype("int64")
    metadata = metadata.drop_duplicates(["movielens_id", "tmdb_id"], keep=False)
    catalog = mappings.merge(
        metadata, on=["movielens_id", "tmdb_id"], validate="one_to_one"
    )
    catalog = catalog.sort_values("tmdb_id", kind="stable").reset_index(drop=True)
    catalog.insert(2, "item_index", range(len(catalog)))
    if catalog.empty:
        raise ValueError("No one-to-one MovieLens/TMDB catalog rows remain")
    return catalog


def _load_state(path: Path, expected: dict[str, Any]) -> dict[str, Any]:
    """Load resumable state and reject inputs from a different run."""
    if not path.is_file():
        return {**expected, "completed_chunks": [], "prepared_interaction_rows": 0}
    state = json.loads(path.read_text(encoding="utf-8"))
    for key, value in expected.items():
        if state.get(key) != value:
            raise ValueError(f"Cannot resume incompatible preparation state: {key}")
    return state


def prepare_dataset(
    config: DataPipelineConfig, *, chunk_size: int = 1_000_000
) -> PrepareResult:
    """Prepare a versioned catalog and resumable user-bucket interaction parts."""
    if chunk_size < 1:
        raise ValueError("chunk_size must be positive")
    source_hashes = _source_hashes(config)
    pipeline_sha256 = implementation_fingerprint()
    version_id = dataset_version_id(
        config, source_hashes, implementation_fingerprint=pipeline_sha256
    )
    version_dir = config.dataset.versions_dir / version_id
    work_dir = version_dir / ".work" / "prepare"
    state_path = work_dir / "state.json"
    config_hash = sha256(config.path)
    expected = {
        "version_id": version_id,
        "config_sha256": config_hash,
        "source_hashes": source_hashes,
        "pipeline_sha256": pipeline_sha256,
        "chunk_size": chunk_size,
    }
    state = _load_state(state_path, expected)
    catalog_path = version_dir / "catalog.parquet"
    if not catalog_path.is_file():
        _write_parquet(_build_catalog(config), catalog_path, config)
    catalog = pd.read_parquet(catalog_path, columns=["movielens_id", "tmdb_id"])
    mapping = dict(zip(catalog["movielens_id"], catalog["tmdb_id"], strict=True))
    completed = set(state["completed_chunks"])
    resumed_chunks = len(completed)
    total_rows = int(state["prepared_interaction_rows"])
    progress = ProgressReporter("prepare", None)
    for chunk_index, chunk in enumerate(
        pd.read_csv(
            config.dataset.raw_dir / "ratings.csv",
            usecols=["userId", "movieId", "rating", "timestamp"],
            chunksize=chunk_size,
        )
    ):
        if chunk_index in completed:
            progress.report(chunk_index + 1, rows=total_rows)
            continue
        frame = chunk.rename(columns={"userId": "user_id", "movieId": "movielens_id"})
        frame["tmdb_id"] = frame["movielens_id"].map(mapping)
        frame = frame.dropna(subset=["tmdb_id"])
        frame = frame.astype(
            {
                "user_id": "int64",
                "movielens_id": "int64",
                "tmdb_id": "int64",
                "timestamp": "int64",
            }
        )
        for bucket, bucket_frame in frame.groupby(
            frame["user_id"] % config.prepare.user_bucket_count
        ):
            part_path = (
                work_dir
                / "interaction_parts"
                / f"chunk-{chunk_index:06d}-bucket-{int(bucket):03d}.parquet"
            )
            _write_parquet(
                bucket_frame[
                    ["user_id", "tmdb_id", "movielens_id", "rating", "timestamp"]
                ],
                part_path,
                config,
            )
        total_rows += len(frame)
        completed.add(chunk_index)
        state["completed_chunks"] = sorted(completed)
        state["prepared_interaction_rows"] = total_rows
        write_json(state_path, state)
        progress.report(chunk_index + 1, rows=total_rows)
    manifest = {
        **expected,
        "catalog_rows": int(len(catalog)),
        "prepared_interaction_rows": total_rows,
        "resumed_chunks": resumed_chunks,
        "status": "prepared",
    }
    write_json(work_dir / "prepare_manifest.json", manifest)
    log.info("etl.prepare.complete version_id=%s rows=%s", version_id, total_rows)
    return PrepareResult(version_id, version_dir, work_dir, manifest)
