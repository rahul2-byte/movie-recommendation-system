"""Create the inner chronological split used for ranking-data generation."""

from __future__ import annotations

import json
import logging
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from hashlib import sha256 as sha256_bytes
from itertools import zip_longest
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from training.ranking.features import (
    build_feature_frame,
    build_feature_schema,
    write_feature_schema,
)

from data_pipeline.config import (
    DataPipelineConfig,
    RankingDataConfig,
    RankingFeaturesConfig,
)
from data_pipeline.manifests import canonical_json, sha256, write_json
from data_pipeline.progress import ProgressReporter

log = logging.getLogger(__name__)
_INTERACTION_COLUMNS = ["user_id", "tmdb_id", "movielens_id", "rating", "timestamp"]


@dataclass(frozen=True)
class RankingPrepareResult:
    version_id: str
    output_dir: Path
    manifest: dict[str, Any]


@dataclass(frozen=True)
class RankingCandidateResult:
    output_dir: Path
    manifest: dict[str, Any]


@dataclass(frozen=True)
class RankingFeatureResult:
    output_dir: Path
    manifest: dict[str, Any]


def _split_user_events(
    events: pd.DataFrame, config: RankingDataConfig
) -> tuple[pd.DataFrame, pd.DataFrame] | None:
    """Return strict earlier history and later events, or exclude the user."""
    events = events.sort_values(["timestamp", "tmdb_id"], kind="stable")
    total = len(events)
    if total < config.minimum_events_per_user:
        return None
    desired = min(
        max(config.seed_count, int(total * config.inner_train_fraction)), total - 1
    )
    timestamps = events["timestamp"].to_numpy(dtype=np.int64)
    boundary = int(np.searchsorted(timestamps, timestamps[desired - 1], side="right"))
    if boundary >= total:
        boundary = int(np.searchsorted(timestamps, timestamps[-1], side="left"))
    if boundary < config.seed_count or boundary >= total:
        return None
    earlier = events.iloc[:boundary]
    later = events.iloc[boundary:]
    if earlier["timestamp"].max() >= later["timestamp"].min():
        return None
    return earlier, later


def _write_parquet(frame: pd.DataFrame, path: Path, config: RankingDataConfig) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    frame.to_parquet(
        temporary,
        index=False,
        compression=config.compression,
        compression_level=config.compression_level,
    )
    temporary.replace(path)


def _output_dir(version_dir: Path, train_path: Path, config: RankingDataConfig) -> Path:
    fingerprint = f"{sha256(config.path)[:12]}-{sha256(train_path)[:12]}"
    return version_dir / "ranking" / fingerprint


def prepare_ranking_data(
    data_config: DataPipelineConfig,
    ranking_config: RankingDataConfig,
    version_id: str,
) -> RankingPrepareResult:
    """Create immutable earlier-history and later-event ranking inputs."""
    if ranking_config.dataset_version != version_id:
        raise ValueError(
            "ranking-data dataset_version does not match the requested dataset version"
        )
    version_dir = data_config.dataset.versions_dir / version_id
    train_path = version_dir / "train.parquet"
    if not train_path.is_file():
        raise FileNotFoundError(f"Training split not found: {train_path}")
    output_dir = _output_dir(version_dir, train_path, ranking_config)
    manifest_path = output_dir / "manifest.json"
    expected = {
        "version_id": version_id,
        "ranking_config_sha256": sha256(ranking_config.path),
        "source_train_sha256": sha256(train_path),
    }
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if all(manifest.get(key) == value for key, value in expected.items()):
            return RankingPrepareResult(version_id, output_dir, manifest)
        raise ValueError(f"Existing ranking data is incompatible: {output_dir}")

    events = pd.read_parquet(train_path, columns=_INTERACTION_COLUMNS)
    events = events.sort_values(["user_id", "tmdb_id", "timestamp"], kind="stable")
    events = events.drop_duplicates(["user_id", "tmdb_id"], keep="last")
    events = events.loc[events["rating"] >= ranking_config.positive_rating_threshold]
    events = events.sort_values(["user_id", "timestamp", "tmdb_id"], kind="stable")
    retrieval_frames: list[pd.DataFrame] = []
    ranking_frames: list[pd.DataFrame] = []
    eligible_users = 0
    excluded_users = 0
    total_users = int(events["user_id"].nunique())
    progress = ProgressReporter("ranking_prepare", total_users)
    for completed, (_, user_events) in enumerate(
        events.groupby("user_id", sort=False), 1
    ):
        partition = _split_user_events(user_events, ranking_config)
        if partition is None:
            excluded_users += 1
        else:
            retrieval, ranking_events = partition
            retrieval_frames.append(retrieval[_INTERACTION_COLUMNS])
            ranking_frames.append(ranking_events[_INTERACTION_COLUMNS])
            eligible_users += 1
        if completed % 1_000 == 0 or completed == total_users:
            progress.report(completed, rows=eligible_users)
    if not retrieval_frames:
        raise ValueError("No users satisfy the ranking-data temporal split contract")
    retrieval_path = output_dir / "retrieval_train.parquet"
    ranking_events_path = output_dir / "ranking_events.parquet"
    _write_parquet(
        pd.concat(retrieval_frames, ignore_index=True), retrieval_path, ranking_config
    )
    _write_parquet(
        pd.concat(ranking_frames, ignore_index=True),
        ranking_events_path,
        ranking_config,
    )
    manifest = {
        **expected,
        "status": "complete",
        "inner_train_fraction": ranking_config.inner_train_fraction,
        "positive_rating_threshold": ranking_config.positive_rating_threshold,
        "seed_count": ranking_config.seed_count,
        "eligible_users": eligible_users,
        "excluded_users": excluded_users,
        "retrieval_train_rows": int(sum(len(frame) for frame in retrieval_frames)),
        "ranking_events_rows": int(sum(len(frame) for frame in ranking_frames)),
        "output_sha256": {
            "retrieval_train": sha256(retrieval_path),
            "ranking_events": sha256(ranking_events_path),
        },
    }
    write_json(manifest_path, manifest)
    log.info(
        "etl.ranking_prepare.complete version_id=%s eligible_users=%s",
        version_id,
        eligible_users,
    )
    return RankingPrepareResult(version_id, output_dir, manifest)


def _iter_user_events(path: Path) -> Iterable[tuple[int, pd.DataFrame]]:
    """Stream sorted user groups without loading the complete Parquet file."""
    columns = _INTERACTION_COLUMNS
    pending = pd.DataFrame(columns=columns)
    previous_user_id = 0
    for batch in pq.ParquetFile(path).iter_batches(columns=columns, batch_size=100_000):
        frame = batch.to_pandas()
        if not pending.empty:
            frame = pd.concat((pending, frame), ignore_index=True)
        final_user_id = int(frame["user_id"].iloc[-1])
        complete = frame.loc[frame["user_id"] != final_user_id]
        for user_id, events in complete.groupby("user_id", sort=False):
            user_id = int(user_id)
            if user_id <= previous_user_id:
                raise ValueError(f"Ranking input is not ordered by user: {path}")
            previous_user_id = user_id
            yield user_id, events
        pending = frame.loc[frame["user_id"] == final_user_id]
    if not pending.empty:
        user_id = int(pending["user_id"].iloc[0])
        if user_id <= previous_user_id:
            raise ValueError(f"Ranking input is not ordered by user: {path}")
        yield user_id, pending


def _source_candidates(
    artifact: Any,
    seed_tmdb_ids: list[int],
    candidate_k: int,
    cache: dict[int, np.ndarray],
) -> tuple[np.ndarray, np.ndarray]:
    candidates: list[np.ndarray] = []
    ranks: list[np.ndarray] = []
    forbidden = np.asarray(seed_tmdb_ids, dtype=np.int64)
    for seed_tmdb_id in seed_tmdb_ids:
        if seed_tmdb_id not in cache:
            cache[seed_tmdb_id] = np.asarray(
                [
                    candidate_id
                    for candidate_id, _ in artifact.retrieve_one(
                        seed_tmdb_id, candidate_k
                    )
                ],
                dtype=np.int64,
            )
        row = cache[seed_tmdb_id]
        valid = row[(row > 0) & ~np.isin(row, forbidden)]
        if not len(valid):
            continue
        _, first_positions = np.unique(valid, return_index=True)
        valid = valid[np.sort(first_positions)][:candidate_k]
        candidates.append(valid)
        ranks.append(np.arange(1, len(valid) + 1, dtype=np.int32))
    if not candidates:
        return np.empty(0, dtype=np.int64), np.empty(0, dtype=np.int16)
    candidate_ids = np.concatenate(candidates)
    candidate_ranks = np.concatenate(ranks)
    unique_ids, inverse = np.unique(candidate_ids, return_inverse=True)
    support = np.zeros(len(unique_ids), dtype=np.int16)
    np.add.at(support, inverse, 1)
    best_rank = np.full(len(unique_ids), np.iinfo(np.int32).max, dtype=np.int32)
    np.minimum.at(best_rank, inverse, candidate_ranks)
    order = np.lexsort((unique_ids, best_rank, -support))[:candidate_k]
    ranked_ids = unique_ids[order]
    ranked_ranks = np.arange(1, len(ranked_ids) + 1, dtype=np.int16)
    sorted_order = np.argsort(ranked_ids)
    return ranked_ids[sorted_order], ranked_ranks[sorted_order]


def _candidate_output_dir(
    prepared_dir: Path, config: RankingDataConfig, artifacts: Mapping[str, Any]
) -> Path:
    fingerprint = canonical_json(
        {
            "ranking_config_sha256": sha256(config.path),
            "artifacts": {name: artifacts[name].manifest for name in sorted(artifacts)},
        }
    )
    digest = sha256_bytes(fingerprint.encode("utf-8")).hexdigest()[:12]
    return prepared_dir / "candidates" / digest


def _limit_candidates_by_rrf(
    candidate_ids: np.ndarray,
    source_rows: Mapping[str, tuple[np.ndarray, np.ndarray]],
    candidate_limit: int,
) -> np.ndarray:
    """Cap candidates by retrieval-only RRF; labels are never an input."""
    if len(candidate_ids) <= candidate_limit:
        return candidate_ids
    scores = np.zeros(len(candidate_ids), dtype=np.float32)
    for source_ids, source_ranks in source_rows.values():
        if not len(source_ids):
            continue
        positions = np.searchsorted(source_ids, candidate_ids)
        present = (positions < len(source_ids)) & (
            source_ids[np.minimum(positions, len(source_ids) - 1)] == candidate_ids
        )
        ranks = np.zeros(len(candidate_ids), dtype=np.int16)
        ranks[present] = source_ranks[positions[present]]
        scores += np.divide(
            1.0,
            60 + ranks,
            out=np.zeros(len(ranks), dtype=np.float32),
            where=ranks > 0,
        )
    selected = np.lexsort((candidate_ids, -scores))[:candidate_limit]
    return np.sort(candidate_ids[selected])


def _candidate_schema(sources: tuple[str, ...]) -> pa.Schema:
    return pa.schema(
        [
            pa.field("query_index", pa.int64()),
            pa.field("candidate_tmdb_id", pa.int64()),
            pa.field("label", pa.uint8()),
            pa.field("retrieval_source_count", pa.uint8()),
            *[
                field
                for source in sources
                for field in (
                    pa.field(f"retrieval_{source}_rank", pa.int16()),
                    pa.field(f"retrieval_{source}_score_normalized", pa.float32()),
                )
            ],
        ]
    )


def build_ranking_candidates(
    prepared_dir: Path,
    config: RankingDataConfig,
    artifacts: Mapping[str, Any],
) -> RankingCandidateResult:
    """Write compact, resumable candidate and query Parquet datasets."""
    prepared_manifest = json.loads((prepared_dir / "manifest.json").read_text())
    retrieval_path = prepared_dir / "retrieval_train.parquet"
    events_path = prepared_dir / "ranking_events.parquet"
    retrieval_sha256 = sha256(retrieval_path)
    required_sources = set(config.retrievers)
    if set(artifacts) != required_sources:
        raise ValueError(f"Expected ranking artifacts for: {sorted(required_sources)}")
    for source, artifact in artifacts.items():
        artifact_manifest = getattr(artifact, "manifest", {})
        if (
            artifact_manifest.get("dataset_version") != config.dataset_version
            or artifact_manifest.get("train_sha256") != retrieval_sha256
        ):
            raise ValueError(f"{source} artifact was not trained on retrieval_train")
    output_dir = _candidate_output_dir(prepared_dir, config, artifacts)
    output_path = output_dir / "ranking_train.parquet"
    queries_path = output_dir / "ranking_queries.parquet"
    manifest_path = output_dir / "manifest.json"
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if (
            manifest.get("status") == "complete"
            and output_path.is_file()
            and queries_path.is_file()
        ):
            return RankingCandidateResult(output_dir, manifest)
        raise ValueError(f"Existing candidate output is incomplete: {output_dir}")

    sources = tuple(config.retrievers)
    candidate_schema = _candidate_schema(sources)
    query_schema = pa.schema(
        [
            pa.field("query_index", pa.int64()),
            pa.field("user_id", pa.int64()),
            pa.field("seed_tmdb_ids", pa.list_(pa.int64())),
            pa.field("ground_truth_tmdb_ids", pa.list_(pa.int64())),
            pa.field("history_end_timestamp", pa.int64()),
            pa.field("target_start_timestamp", pa.int64()),
        ]
    )
    artifact_manifests = {
        name: artifact.manifest for name, artifact in artifacts.items()
    }
    expected = {
        "ranking_config_sha256": sha256(config.path),
        "retrieval_train_sha256": retrieval_sha256,
        "ranking_events_sha256": sha256(events_path),
        "artifact_manifests": artifact_manifests,
    }
    state_path = output_dir / ".work" / "state.json"
    if state_path.is_file():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if any(state.get(key) != value for key, value in expected.items()):
            raise ValueError(
                f"Cannot resume incompatible candidate state: {output_dir}"
            )
    else:
        state = {
            **expected,
            "completed_queries": 0,
            "completed_parts": 0,
            "candidate_rows": 0,
            "positive_candidate_rows": 0,
            "positive_target_rows": 0,
            "zero_candidate_queries": 0,
            "zero_positive_candidate_queries": 0,
        }
    source_caches: dict[str, dict[int, np.ndarray]] = {name: {} for name in sources}
    candidate_buffers: dict[str, list[np.ndarray]] = {
        field.name: [] for field in candidate_schema
    }
    query_buffers: dict[str, list[Any]] = {field.name: [] for field in query_schema}
    progress = ProgressReporter(
        "ranking_candidates", int(prepared_manifest["eligible_users"])
    )

    def write_part(completed_queries: int) -> None:
        if not query_buffers["query_index"]:
            return
        part_index = int(state["completed_parts"])
        part_name = f"part-{part_index:06d}.parquet"
        query_part = output_dir / ".work" / "queries" / part_name
        candidate_part = output_dir / ".work" / "candidates" / part_name
        query_table = pa.Table.from_arrays(
            [
                pa.array(query_buffers[field.name], type=field.type)
                for field in query_schema
            ],
            schema=query_schema,
        )
        candidate_table = pa.Table.from_arrays(
            [
                pa.array(
                    (
                        np.concatenate(candidate_buffers[field.name])
                        if candidate_buffers[field.name]
                        else np.empty(0, dtype=np.int64)
                    ),
                    type=field.type,
                )
                for field in candidate_schema
            ],
            schema=candidate_schema,
        )
        for destination, table in (
            (query_part, query_table),
            (candidate_part, candidate_table),
        ):
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary = destination.with_name(f".{destination.name}.tmp")
            pq.write_table(
                table,
                temporary,
                compression=config.compression,
                compression_level=config.compression_level,
            )
            temporary.replace(destination)
        state["completed_queries"] = completed_queries
        state["completed_parts"] = part_index + 1
        write_json(state_path, state)
        for values in candidate_buffers.values():
            values.clear()
        for values in query_buffers.values():
            values.clear()

    start_query = int(state["completed_queries"])
    for query_index, pair in enumerate(
        zip_longest(_iter_user_events(retrieval_path), _iter_user_events(events_path))
    ):
        history_record, event_record = pair
        if history_record is None or event_record is None:
            raise ValueError(
                "retrieval history and ranking events have different users"
            )
        history_user, history = history_record
        event_user, targets = event_record
        if history_user != event_user:
            raise ValueError(
                "retrieval history and ranking events have different users"
            )
        if query_index < start_query:
            continue
        seeds = history["tmdb_id"].to_numpy(dtype=np.int64)[-config.seed_count :]
        if len(seeds) != config.seed_count:
            raise ValueError(f"Ranking query {history_user} does not have five seeds")
        target_ids = targets["tmdb_id"].to_numpy(dtype=np.int64)
        source_rows = {
            source: _source_candidates(
                artifacts[source],
                seeds.tolist(),
                config.candidate_k,
                source_caches[source],
            )
            for source in sources
        }
        candidate_ids = np.unique(
            np.concatenate([source_rows[source][0] for source in sources])
        )
        candidate_ids = _limit_candidates_by_rrf(
            candidate_ids, source_rows, config.candidate_limit
        )
        query_buffers["query_index"].append(query_index)
        query_buffers["user_id"].append(history_user)
        query_buffers["seed_tmdb_ids"].append(seeds.tolist())
        query_buffers["ground_truth_tmdb_ids"].append(target_ids.tolist())
        query_buffers["history_end_timestamp"].append(int(history["timestamp"].max()))
        query_buffers["target_start_timestamp"].append(int(targets["timestamp"].min()))
        state["positive_target_rows"] += len(target_ids)
        if not len(candidate_ids):
            state["zero_candidate_queries"] += 1
            state["zero_positive_candidate_queries"] += 1
        else:
            labels = np.isin(candidate_ids, target_ids).astype(np.uint8)
            source_count = np.zeros(len(candidate_ids), dtype=np.uint8)
            candidate_buffers["query_index"].append(
                np.full(len(candidate_ids), query_index, dtype=np.int64)
            )
            candidate_buffers["candidate_tmdb_id"].append(
                candidate_ids.astype(np.int64)
            )
            candidate_buffers["label"].append(labels)
            for source in sources:
                source_ids, source_ranks = source_rows[source]
                positions = np.searchsorted(source_ids, candidate_ids)
                present = (
                    (positions < len(source_ids))
                    & (
                        source_ids[np.minimum(positions, len(source_ids) - 1)]
                        == candidate_ids
                    )
                    if len(source_ids)
                    else np.zeros(len(candidate_ids), dtype=bool)
                )
                ranks = np.zeros(len(candidate_ids), dtype=np.int16)
                ranks[present] = source_ranks[positions[present]]
                source_count += present.astype(np.uint8)
                candidate_buffers[f"retrieval_{source}_rank"].append(ranks)
                candidate_buffers[f"retrieval_{source}_score_normalized"].append(
                    np.divide(
                        1.0,
                        ranks,
                        out=np.zeros(len(ranks), dtype=np.float32),
                        where=ranks > 0,
                    ).astype(np.float32)
                )
            candidate_buffers["retrieval_source_count"].append(source_count)
            state["candidate_rows"] += len(candidate_ids)
            positives = int(labels.sum())
            state["positive_candidate_rows"] += positives
            state["zero_positive_candidate_queries"] += int(positives == 0)
        completed_queries = query_index + 1
        if completed_queries % config.candidate_query_batch_size == 0:
            write_part(completed_queries)
        if (
            completed_queries % 1_000 == 0
            or completed_queries == prepared_manifest["eligible_users"]
        ):
            progress.report(completed_queries, rows=int(state["candidate_rows"]))
    write_part(int(prepared_manifest["eligible_users"]))

    def compact(parts_dir: Path, destination: Path, schema: pa.Schema) -> None:
        temporary = destination.with_name(f".{destination.name}.compact.tmp")
        writer = pq.ParquetWriter(
            temporary,
            schema,
            compression=config.compression,
            compression_level=config.compression_level,
        )
        try:
            for part in sorted(parts_dir.glob("*.parquet")):
                writer.write_table(pq.read_table(part))
        finally:
            writer.close()
        temporary.replace(destination)

    compact(output_dir / ".work" / "queries", queries_path, query_schema)
    compact(output_dir / ".work" / "candidates", output_path, candidate_schema)
    manifest = {
        "status": "complete",
        "dataset_version": config.dataset_version,
        **expected,
        "query_count": int(state["completed_queries"]),
        "candidate_rows": int(state["candidate_rows"]),
        "positive_candidate_rows": int(state["positive_candidate_rows"]),
        "positive_target_rows": int(state["positive_target_rows"]),
        "unretrieved_positive_targets": int(state["positive_target_rows"])
        - int(state["positive_candidate_rows"]),
        "zero_candidate_queries": int(state["zero_candidate_queries"]),
        "zero_positive_candidate_queries": int(
            state["zero_positive_candidate_queries"]
        ),
        "candidate_k_per_source": config.candidate_k,
        "candidate_limit": config.candidate_limit,
        "source_score_semantics": "reciprocal_source_rank",
        "schema_version": "ranking-candidates-v2",
        "output_sha256": {
            "ranking_queries": sha256(queries_path),
            "ranking_train": sha256(output_path),
        },
    }
    write_json(manifest_path, manifest)
    log.info(
        "etl.ranking_candidates.complete queries=%s rows=%s",
        state["completed_queries"],
        state["candidate_rows"],
    )
    return RankingCandidateResult(output_dir, manifest)


def _build_partition_candidates(
    version_dir: Path,
    config: RankingDataConfig,
    artifacts: Mapping[str, Any],
    partition: str,
) -> RankingCandidateResult:
    """Generate held-out candidates without using the partition targets in retrieval."""
    if partition not in {"validation", "test"}:
        raise ValueError(f"Unsupported ranking evaluation partition: {partition}")
    version_dir = version_dir.resolve()
    train_path = version_dir / "train.parquet"
    query_path = version_dir / f"{partition}.parquet"
    if not train_path.is_file() or not query_path.is_file():
        raise FileNotFoundError(
            f"{partition.title()} candidates require train.parquet and {partition}.parquet"
        )
    required_sources = set(config.retrievers)
    if set(artifacts) != required_sources:
        raise ValueError(
            f"Expected {partition} artifacts for: {sorted(required_sources)}"
        )
    train_sha256 = sha256(train_path)
    for source, artifact in artifacts.items():
        manifest = artifact.manifest
        if (
            manifest.get("dataset_version") != config.dataset_version
            or manifest.get("train_sha256") != train_sha256
        ):
            raise ValueError(f"{source} artifact was not trained on full train.parquet")
    sources = tuple(config.retrievers)
    expected = {
        "dataset_version": config.dataset_version,
        "ranking_config_sha256": sha256(config.path),
        "full_train_sha256": train_sha256,
        f"{partition}_query_sha256": sha256(query_path),
        "artifact_manifests": {name: artifacts[name].manifest for name in sources},
    }
    digest = sha256_bytes(canonical_json(expected).encode("utf-8")).hexdigest()[:12]
    output_dir = version_dir / "ranking" / partition / digest
    output_path = output_dir / f"ranking_{partition}.parquet"
    manifest_path = output_dir / "manifest.json"
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("status") == "complete" and output_path.is_file():
            return RankingCandidateResult(output_dir, manifest)
        raise ValueError(f"Existing {partition} output is incomplete: {output_dir}")

    state_path = output_dir / ".work" / "state.json"
    if state_path.is_file():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if any(state.get(key) != value for key, value in expected.items()):
            raise ValueError(
                f"Cannot resume incompatible {partition} state: {output_dir}"
            )
    else:
        state = {
            **expected,
            "completed_queries": 0,
            "completed_parts": 0,
            "candidate_rows": 0,
            "positive_candidate_rows": 0,
            "positive_target_rows": 0,
            "zero_candidate_queries": 0,
            "zero_positive_candidate_queries": 0,
        }
    schema = _candidate_schema(sources)
    buffers: dict[str, list[np.ndarray]] = {field.name: [] for field in schema}
    source_caches: dict[str, dict[int, np.ndarray]] = {name: {} for name in sources}
    validation_file = pq.ParquetFile(query_path)
    progress = ProgressReporter(
        f"ranking_{partition}_candidates", validation_file.metadata.num_rows
    )

    def write_part(completed_queries: int) -> None:
        if buffers["query_index"]:
            part_index = int(state["completed_parts"])
            destination = (
                output_dir / ".work" / "parts" / f"part-{part_index:06d}.parquet"
            )
            destination.parent.mkdir(parents=True, exist_ok=True)
            table = pa.Table.from_arrays(
                [
                    pa.array(np.concatenate(buffers[field.name]), type=field.type)
                    for field in schema
                ],
                schema=schema,
            )
            temporary = destination.with_name(f".{destination.name}.tmp")
            pq.write_table(
                table,
                temporary,
                compression=config.compression,
                compression_level=config.compression_level,
            )
            temporary.replace(destination)
            state["completed_parts"] = part_index + 1
            for values in buffers.values():
                values.clear()
        state["completed_queries"] = completed_queries
        write_json(state_path, state)

    query_index = 0
    for batch in validation_file.iter_batches(
        columns=["seed_tmdb_ids", "ground_truth_tmdb_ids"], batch_size=1_000
    ):
        for query in batch.to_pylist():
            if query_index < int(state["completed_queries"]):
                query_index += 1
                continue
            seeds = np.asarray(query["seed_tmdb_ids"], dtype=np.int64)
            targets = np.asarray(query["ground_truth_tmdb_ids"], dtype=np.int64)
            if len(seeds) != config.seed_count:
                raise ValueError(
                    f"{partition.title()} query {query_index} does not have five seeds"
                )
            source_rows = {
                source: _source_candidates(
                    artifacts[source],
                    seeds.tolist(),
                    config.candidate_k,
                    source_caches[source],
                )
                for source in sources
            }
            candidate_ids = np.unique(
                np.concatenate([source_rows[source][0] for source in sources])
            )
            candidate_ids = _limit_candidates_by_rrf(
                candidate_ids, source_rows, config.candidate_limit
            )
            state["positive_target_rows"] += len(targets)
            if not len(candidate_ids):
                state["zero_candidate_queries"] += 1
                state["zero_positive_candidate_queries"] += 1
            else:
                labels = np.isin(candidate_ids, targets).astype(np.uint8)
                source_count = np.zeros(len(candidate_ids), dtype=np.uint8)
                buffers["query_index"].append(
                    np.full(len(candidate_ids), query_index, dtype=np.int64)
                )
                buffers["candidate_tmdb_id"].append(candidate_ids.astype(np.int64))
                buffers["label"].append(labels)
                for source in sources:
                    source_ids, source_ranks = source_rows[source]
                    positions = np.searchsorted(source_ids, candidate_ids)
                    present = (
                        (positions < len(source_ids))
                        & (
                            source_ids[np.minimum(positions, len(source_ids) - 1)]
                            == candidate_ids
                        )
                        if len(source_ids)
                        else np.zeros(len(candidate_ids), dtype=bool)
                    )
                    ranks = np.zeros(len(candidate_ids), dtype=np.int16)
                    ranks[present] = source_ranks[positions[present]]
                    source_count += present.astype(np.uint8)
                    buffers[f"retrieval_{source}_rank"].append(ranks)
                    buffers[f"retrieval_{source}_score_normalized"].append(
                        np.divide(
                            1.0,
                            ranks,
                            out=np.zeros(len(ranks), dtype=np.float32),
                            where=ranks > 0,
                        ).astype(np.float32)
                    )
                buffers["retrieval_source_count"].append(source_count)
                state["candidate_rows"] += len(candidate_ids)
                positives = int(labels.sum())
                state["positive_candidate_rows"] += positives
                state["zero_positive_candidate_queries"] += int(positives == 0)
            query_index += 1
            if query_index % config.candidate_query_batch_size == 0:
                write_part(query_index)
            if (
                query_index % 1_000 == 0
                or query_index == validation_file.metadata.num_rows
            ):
                progress.report(query_index, rows=int(state["candidate_rows"]))
    write_part(query_index)

    output_dir.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_name(f".{output_path.name}.compact.tmp")
    writer = pq.ParquetWriter(
        temporary,
        schema,
        compression=config.compression,
        compression_level=config.compression_level,
    )
    try:
        for part in sorted((output_dir / ".work" / "parts").glob("*.parquet")):
            writer.write_table(pq.read_table(part))
    finally:
        writer.close()
    temporary.replace(output_path)
    manifest = {
        "status": "complete",
        "partition": partition,
        **expected,
        "query_count": int(state["completed_queries"]),
        "candidate_rows": int(state["candidate_rows"]),
        "positive_candidate_rows": int(state["positive_candidate_rows"]),
        "positive_target_rows": int(state["positive_target_rows"]),
        "unretrieved_positive_targets": int(state["positive_target_rows"])
        - int(state["positive_candidate_rows"]),
        "zero_candidate_queries": int(state["zero_candidate_queries"]),
        "zero_positive_candidate_queries": int(
            state["zero_positive_candidate_queries"]
        ),
        "candidate_k_per_source": config.candidate_k,
        "candidate_limit": config.candidate_limit,
        "source_score_semantics": "reciprocal_source_rank",
        "schema_version": f"ranking-{partition}-candidates-v1",
        "output_sha256": {f"ranking_{partition}": sha256(output_path)},
    }
    write_json(manifest_path, manifest)
    return RankingCandidateResult(output_dir, manifest)


def build_validation_candidates(
    version_dir: Path,
    config: RankingDataConfig,
    artifacts: Mapping[str, Any],
) -> RankingCandidateResult:
    """Generate held-out validation candidates from full-history retrievers."""
    return _build_partition_candidates(version_dir, config, artifacts, "validation")


def build_test_candidates(
    version_dir: Path,
    config: RankingDataConfig,
    artifacts: Mapping[str, Any],
) -> RankingCandidateResult:
    """Generate the final, held-out test candidates from selected artifacts."""
    return _build_partition_candidates(version_dir, config, artifacts, "test")


def materialize_ranking_features(
    candidate_dir: Path,
    ranking_data_dir: Path,
    config: RankingFeaturesConfig,
    *,
    candidate_file_name: str = "ranking_train.parquet",
    popularity_train_path: Path | None = None,
) -> RankingFeatureResult:
    """Materialize chunked, resumable ranking features from immutable inputs."""
    candidate_dir = candidate_dir.resolve()
    ranking_data_dir = ranking_data_dir.resolve()
    candidate_path = candidate_dir / candidate_file_name
    candidate_manifest_path = candidate_dir / "manifest.json"
    retrieval_path = (
        popularity_train_path or ranking_data_dir / "retrieval_train.parquet"
    ).resolve()
    if not candidate_path.is_file() or not candidate_manifest_path.is_file():
        raise FileNotFoundError(f"Candidate dataset is incomplete: {candidate_dir}")
    if not retrieval_path.is_file():
        raise FileNotFoundError(f"Retrieval training data is missing: {retrieval_path}")
    candidate_manifest = json.loads(candidate_manifest_path.read_text(encoding="utf-8"))
    feature_code_path = Path(__file__).parents[1] / "training/ranking/features.py"
    expected = {
        "dataset_version": candidate_manifest["dataset_version"],
        "candidate_sha256": sha256(candidate_path),
        "popularity_train_sha256": sha256(retrieval_path),
        "feature_config_sha256": sha256(config.path),
        "feature_code_sha256": sha256(feature_code_path),
    }
    digest = sha256_bytes(canonical_json(expected).encode("utf-8")).hexdigest()[:12]
    output_dir = candidate_dir / "features" / digest
    output_path = output_dir / "ranking_features.parquet"
    schema_path = output_dir / "feature_schema.json"
    manifest_path = output_dir / "manifest.json"
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if (
            manifest.get("status") == "complete"
            and output_path.is_file()
            and schema_path.is_file()
        ):
            return RankingFeatureResult(output_dir, manifest)
        raise ValueError(f"Existing feature output is incomplete: {output_dir}")

    counts: Counter[int] = Counter()
    retrieval_file = pq.ParquetFile(retrieval_path)
    for batch in retrieval_file.iter_batches(columns=["tmdb_id"], batch_size=250_000):
        counts.update(
            int(item_id) for item_id in batch.column(0).to_pylist() if item_id
        )
    popularity = pd.Series(counts, dtype=np.float32)
    schema = build_feature_schema(config.schema_version, config.feature_names)
    state_path = output_dir / ".work" / "state.json"
    if state_path.is_file():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if any(state.get(key) != value for key, value in expected.items()):
            raise ValueError(f"Cannot resume incompatible feature state: {output_dir}")
    else:
        state = {**expected, "completed_row_groups": 0, "feature_rows": 0}

    candidate_file = pq.ParquetFile(candidate_path)
    progress = ProgressReporter(
        "ranking_features", candidate_file.metadata.num_row_groups
    )
    parts_dir = output_dir / ".work" / "parts"
    for row_group in range(
        int(state["completed_row_groups"]), candidate_file.metadata.num_row_groups
    ):
        frame = build_feature_frame(
            candidate_file.read_row_group(row_group).to_pandas(), popularity, schema
        )
        destination = parts_dir / f"part-{row_group:06d}.parquet"
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(f".{destination.name}.tmp")
        frame.to_parquet(
            temporary,
            index=False,
            compression=config.compression,
            compression_level=config.compression_level,
        )
        temporary.replace(destination)
        state["completed_row_groups"] = row_group + 1
        state["feature_rows"] += len(frame)
        write_json(state_path, state)
        progress.report(row_group + 1, rows=int(state["feature_rows"]))

    temporary = output_path.with_name(f".{output_path.name}.compact.tmp")
    writer: pq.ParquetWriter | None = None
    try:
        for part in sorted(parts_dir.glob("*.parquet")):
            table = pq.read_table(part)
            if writer is None:
                writer = pq.ParquetWriter(
                    temporary,
                    table.schema,
                    compression=config.compression,
                    compression_level=config.compression_level,
                )
            writer.write_table(table)
    finally:
        if writer is not None:
            writer.close()
    if writer is None:
        raise ValueError("Candidate dataset has no row groups")
    temporary.replace(output_path)
    write_feature_schema(
        schema_path,
        schema,
        expected["dataset_version"],
        expected["feature_config_sha256"],
        expected["feature_code_sha256"],
    )
    manifest = {
        "status": "complete",
        **expected,
        "schema_version": schema.schema_version,
        "feature_names": list(schema.feature_names),
        "feature_rows": int(state["feature_rows"]),
        "popularity_item_count": len(popularity),
        "output_sha256": {
            "ranking_features": sha256(output_path),
            "feature_schema": sha256(schema_path),
        },
    }
    write_json(manifest_path, manifest)
    log.info(
        "etl.ranking_features.complete rows=%s output=%s",
        state["feature_rows"],
        output_dir,
    )
    return RankingFeatureResult(output_dir, manifest)
