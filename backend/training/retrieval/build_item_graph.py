"""Authoritative BM25-weighted item-graph retrieval training."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
import yaml
from implicit.nearest_neighbours import ItemItemRecommender, bm25_weight
from retrieval.seeded import collect_seed_candidates, order_candidate_ids

from training.retrieval.build_als import _build_user_items, _load_interactions, _sha256
from training.retrieval.build_tfidf import _merge_neighbor_rows, _seed_ids


@dataclass(frozen=True)
class ItemGraphTrainingConfig:
    dataset_version: str
    output_dir: Path
    neighbor_count: int
    k1: float
    b: float
    num_threads: int
    random_seed: int
    per_seed_candidates: int
    parquet_batch_size: int
    mlflow_experiment_name: str


def load_item_graph_training_config(path: Path) -> ItemGraphTrainingConfig:
    path = path.resolve()
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    values = payload.get("item_graph") if isinstance(payload, dict) else None
    if not isinstance(values, dict):
        raise ValueError(
            "retrieval training configuration must contain an item_graph mapping"
        )
    required = (
        "dataset_version",
        "output_dir",
        "neighbor_count",
        "k1",
        "b",
        "num_threads",
        "random_seed",
        "per_seed_candidates",
        "parquet_batch_size",
        "mlflow_experiment_name",
    )
    missing = [key for key in required if key not in values]
    if missing:
        raise ValueError(f"item_graph configuration is missing values: {missing}")
    for key in ("neighbor_count", "per_seed_candidates", "parquet_batch_size"):
        if not isinstance(values[key], int) or values[key] < 1:
            raise ValueError(f"item_graph.{key} must be a positive integer")
    if not isinstance(values["num_threads"], int) or values["num_threads"] < 0:
        raise ValueError("item_graph.num_threads must be zero or a positive integer")
    if not isinstance(values["random_seed"], int):
        raise ValueError("item_graph.random_seed must be an integer")
    for key in ("k1", "b"):
        if not isinstance(values[key], (int, float)) or values[key] <= 0:
            raise ValueError(f"item_graph.{key} must be positive")
    for key in ("dataset_version", "output_dir", "mlflow_experiment_name"):
        if not isinstance(values[key], str) or not values[key]:
            raise ValueError(f"item_graph.{key} must be a non-empty string")
    return ItemGraphTrainingConfig(
        dataset_version=values["dataset_version"],
        output_dir=(path.parent / values["output_dir"]).resolve(),
        neighbor_count=values["neighbor_count"],
        k1=float(values["k1"]),
        b=float(values["b"]),
        num_threads=values["num_threads"],
        random_seed=values["random_seed"],
        per_seed_candidates=values["per_seed_candidates"],
        parquet_batch_size=values["parquet_batch_size"],
        mlflow_experiment_name=values["mlflow_experiment_name"],
    )


@dataclass(frozen=True)
class ItemGraphArtifact:
    output_dir: Path
    neighbor_positions: np.ndarray
    tmdb_id_to_idx: dict[int, int]
    idx_to_tmdb_id: dict[int, int]
    manifest: dict[str, object]

    @classmethod
    def load(cls, output_dir: Path) -> ItemGraphArtifact:
        output_dir = output_dir.resolve()
        required = ("neighbor_positions.npy", "tmdb_id_to_idx.json", "manifest.json")
        missing = [name for name in required if not (output_dir / name).is_file()]
        if missing:
            raise FileNotFoundError(
                f"Incomplete item-graph artifact at {output_dir}: {missing}"
            )
        manifest = json.loads(
            (output_dir / "manifest.json").read_text(encoding="utf-8")
        )
        if (
            manifest.get("model_type") != "item_graph"
            or manifest.get("id_schema_version") != "tmdb-keyed-v1"
        ):
            raise ValueError(
                f"Incompatible item-graph artifact manifest: {output_dir / 'manifest.json'}"
            )
        positions = np.load(output_dir / "neighbor_positions.npy")
        mapping = {
            int(key): int(value)
            for key, value in json.loads(
                (output_dir / "tmdb_id_to_idx.json").read_text(encoding="utf-8")
            ).items()
        }
        if positions.ndim != 2 or len(mapping) != len(positions):
            raise ValueError("Item-graph neighbor matrix and ID-map sizes differ")
        return cls(
            output_dir,
            positions,
            mapping,
            {position: tmdb_id for tmdb_id, position in mapping.items()},
            manifest,
        )

    def retrieve_one(self, seed_tmdb_id: int, top_k: int) -> list[tuple[int, float]]:
        if top_k < 1:
            raise ValueError("top_k must be positive")
        position = self.tmdb_id_to_idx.get(int(seed_tmdb_id))
        if position is None:
            return []
        neighbors = self.neighbor_positions[position]
        return [
            (self.idx_to_tmdb_id[int(neighbor)], 1.0 / rank)
            for rank, neighbor in enumerate(neighbors, start=1)
            if int(neighbor) >= 0
        ][:top_k]

    def recommend(self, seed_tmdb_ids: Iterable[int], top_k: int) -> list[int]:
        evidence = collect_seed_candidates(
            seed_tmdb_ids,
            retrieve_one=self.retrieve_one,
            source="item_graph",
            top_k=max(top_k, int(self.manifest["per_seed_candidates"])),
        )
        return order_candidate_ids(evidence)[:top_k]


def _ranked_neighbor_positions(
    similarity, neighbor_count: int, report: Callable[[int], None]
) -> np.ndarray:
    positions = np.full((similarity.shape[0], neighbor_count), -1, dtype=np.int32)
    for item_position in range(similarity.shape[0]):
        row = similarity[item_position]
        order = np.argsort(row.data)[::-1]
        neighbors = row.indices[order]
        neighbors = neighbors[neighbors != item_position][:neighbor_count]
        positions[item_position, : len(neighbors)] = neighbors
        if item_position % 5_000 == 0 or item_position + 1 == similarity.shape[0]:
            report(item_position + 1)
    return positions


def train_item_graph(
    train_path: Path,
    output_dir: Path,
    *,
    neighbor_count: int,
    k1: float,
    b: float,
    num_threads: int,
    random_seed: int,
    dataset_version: str,
    per_seed_candidates: int,
    parquet_batch_size: int,
    progress_callback: Callable[[int, str], None] | None = None,
    training_metadata: dict[str, object] | None = None,
) -> ItemGraphArtifact:
    """Build and publish an immutable train-only BM25 item graph."""
    if output_dir.exists():
        raise FileExistsError(
            f"Refusing to overwrite immutable artifact directory: {output_dir}"
        )
    if neighbor_count < 1 or per_seed_candidates < 1 or not dataset_version:
        raise ValueError(
            "neighbor_count, per_seed_candidates, and dataset_version are required"
        )

    def report(completed: int, stage: str) -> None:
        if progress_callback is not None:
            progress_callback(completed, stage)

    users, items, _ = _load_interactions(train_path, parquet_batch_size)
    report(1, "read train interactions")
    user_items, user_ids, tmdb_ids = _build_user_items(
        users, items, np.ones(len(items), dtype=np.float32)
    )
    report(2, "build binary user-item graph")
    weighted_items = bm25_weight(user_items.T, K1=k1, B=b).T.tocsr()
    model = ItemItemRecommender(K=neighbor_count + 1, num_threads=num_threads)
    model.fit(weighted_items, show_progress=True)
    report(3, "fit BM25 item graph")
    neighbors = _ranked_neighbor_positions(
        model.similarity,
        neighbor_count,
        lambda completed: report(
            4, f"materialize neighbors {completed}/{len(tmdb_ids)}"
        ),
    )
    report(4, "materialize ranked neighbors")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_dir.parent / f".{output_dir.name}.tmp"
    temporary.mkdir()
    try:
        np.save(temporary / "neighbor_positions.npy", neighbors)
        mapping = {
            str(int(tmdb_id)): position for position, tmdb_id in enumerate(tmdb_ids)
        }
        (temporary / "tmdb_id_to_idx.json").write_text(
            json.dumps(mapping, sort_keys=True), encoding="utf-8"
        )
        manifest: dict[str, object] = {
            "model_type": "item_graph",
            "id_schema_version": "tmdb-keyed-v1",
            "dataset_version": dataset_version,
            "train_sha256": _sha256(train_path),
            "neighbor_count": neighbor_count,
            "k1": k1,
            "b": b,
            "num_threads": num_threads,
            "random_seed": random_seed,
            "per_seed_candidates": per_seed_candidates,
            "user_count": len(user_ids),
            "item_count": len(tmdb_ids),
            "interaction_count": int(user_items.nnz),
            "interaction_weighting": "binary_positive",
            "ranking": "bm25_item_graph",
        }
        if training_metadata:
            manifest.update(training_metadata)
        for filename in ("neighbor_positions.npy", "tmdb_id_to_idx.json"):
            manifest.setdefault("artifact_sha256", {})[filename] = _sha256(
                temporary / filename
            )
        (temporary / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        temporary.replace(output_dir)
    except Exception:
        for path in temporary.iterdir():
            path.unlink()
        temporary.rmdir()
        raise
    artifact = ItemGraphArtifact.load(output_dir)
    report(6, "verify artifact")
    return artifact


@dataclass(frozen=True)
class ItemGraphSeedCache:
    artifact: ItemGraphArtifact
    row_by_seed: dict[int, int]
    neighbor_ids: np.ndarray

    def recommend(self, seed_tmdb_ids: Iterable[int], top_k: int) -> list[int]:
        seeds = _seed_ids(seed_tmdb_ids)
        rows = [self.row_by_seed.get(seed_id) for seed_id in seeds]
        if not seeds or any(row is None for row in rows):
            return self.artifact.recommend(seeds, top_k)
        return _merge_neighbor_rows(
            seeds, self.neighbor_ids[np.asarray(rows, dtype=np.int64)], top_k
        )


def build_item_graph_seed_cache(
    artifact: ItemGraphArtifact,
    queries_path: Path,
    *,
    query_limit: int | None = None,
    batch_size: int = 512,
    progress_callback: Callable[[int, int], None] | None = None,
) -> ItemGraphSeedCache:
    """Copy exact precomputed graph rows for the query seeds into an evaluation cache."""
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    source = pq.ParquetFile(queries_path)
    remaining = query_limit
    parts: list[np.ndarray] = []
    for batch in source.iter_batches(columns=["seed_tmdb_ids"], batch_size=5_000):
        if remaining is not None and remaining == 0:
            break
        current = batch.slice(0, remaining) if remaining is not None else batch
        parts.append(current.column(0).flatten().to_numpy(zero_copy_only=False))
        if remaining is not None:
            remaining -= current.num_rows
    seeds = (
        np.unique(np.concatenate(parts).astype(np.int64))
        if parts
        else np.empty(0, dtype=np.int64)
    )
    known = np.asarray(
        [seed for seed in seeds if int(seed) in artifact.tmdb_id_to_idx], dtype=np.int64
    )
    positions = np.asarray(
        [artifact.tmdb_id_to_idx[int(seed)] for seed in known], dtype=np.int64
    )
    neighbor_positions = artifact.neighbor_positions[positions]
    item_ids = np.asarray(
        [
            artifact.idx_to_tmdb_id[index]
            for index in range(len(artifact.idx_to_tmdb_id))
        ],
        dtype=np.int64,
    )
    neighbor_ids = np.zeros(neighbor_positions.shape, dtype=np.int64)
    valid = neighbor_positions >= 0
    neighbor_ids[valid] = item_ids[neighbor_positions[valid]]
    if progress_callback is not None:
        for completed in range(0, len(known), batch_size):
            progress_callback(min(completed + batch_size, len(known)), len(known))
        if not len(known):
            progress_callback(0, 0)
    return ItemGraphSeedCache(
        artifact, {int(seed): index for index, seed in enumerate(known)}, neighbor_ids
    )
