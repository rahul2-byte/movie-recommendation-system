"""Authoritative local training for TMDB-keyed item-candidate two-tower retrieval."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

import faiss
import numpy as np
import pandas as pd
import torch
import yaml
from retrieval.seeded import collect_seed_candidates, order_candidate_ids
from torch import nn
from torch.nn import functional as functional


@dataclass(frozen=True)
class TwoTowerTrainingConfig:
    dataset_version: str
    output_dir: Path
    embedding_dim: int
    batch_size: int
    epochs: int
    learning_rate: float
    max_pairs_per_user: int
    random_seed: int
    per_seed_candidates: int
    mlflow_experiment_name: str


def load_two_tower_training_config(path: Path) -> TwoTowerTrainingConfig:
    path = path.resolve()
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    values = payload.get("two_tower") if isinstance(payload, dict) else None
    if not isinstance(values, dict):
        raise ValueError(
            "retrieval training configuration must contain a two_tower mapping"
        )
    required = (
        "dataset_version",
        "output_dir",
        "embedding_dim",
        "batch_size",
        "epochs",
        "learning_rate",
        "max_pairs_per_user",
        "random_seed",
        "per_seed_candidates",
        "mlflow_experiment_name",
    )
    missing = [key for key in required if key not in values]
    if missing:
        raise ValueError(f"two_tower configuration is missing values: {missing}")
    positive_ints = (
        "embedding_dim",
        "batch_size",
        "epochs",
        "max_pairs_per_user",
        "per_seed_candidates",
    )
    if any(
        not isinstance(values[key], int) or values[key] < 1 for key in positive_ints
    ):
        raise ValueError(
            f"two_tower.{', two_tower.'.join(positive_ints)} must be positive integers"
        )
    if (
        not isinstance(values["learning_rate"], (int, float))
        or values["learning_rate"] <= 0
    ):
        raise ValueError("two_tower.learning_rate must be positive")
    if not isinstance(values["random_seed"], int):
        raise ValueError("two_tower.random_seed must be an integer")
    for key in ("dataset_version", "output_dir", "mlflow_experiment_name"):
        if not isinstance(values[key], str) or not values[key]:
            raise ValueError(f"two_tower.{key} must be a non-empty string")
    return TwoTowerTrainingConfig(
        dataset_version=values["dataset_version"],
        output_dir=(path.parent / values["output_dir"]).resolve(),
        embedding_dim=values["embedding_dim"],
        batch_size=values["batch_size"],
        epochs=values["epochs"],
        learning_rate=float(values["learning_rate"]),
        max_pairs_per_user=values["max_pairs_per_user"],
        random_seed=values["random_seed"],
        per_seed_candidates=values["per_seed_candidates"],
        mlflow_experiment_name=values["mlflow_experiment_name"],
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_pairs(
    train_path: Path, max_pairs_per_user: int
) -> tuple[np.ndarray, np.ndarray]:
    required = ("user_id", "tmdb_id", "timestamp")
    events = pd.read_parquet(train_path, columns=list(required))
    missing = set(required) - set(events.columns)
    if missing:
        raise ValueError(
            f"Two-tower training data is missing columns: {sorted(missing)}"
        )
    if events.empty or events[list(required)].isna().any().any():
        raise ValueError(
            "Two-tower training data is empty or contains null identifiers"
        )
    events = events.sort_values(["user_id", "timestamp", "tmdb_id"], kind="stable")
    users = events["user_id"].to_numpy(dtype=np.int64, copy=False)
    tmdb_ids, item_positions = np.unique(
        events["tmdb_id"].to_numpy(dtype=np.int64, copy=False), return_inverse=True
    )
    if np.any(users <= 0) or np.any(tmdb_ids <= 0):
        raise ValueError("Two-tower training data contains invalid IDs")
    same_user = users[:-1] == users[1:]
    left = np.flatnonzero(same_user)
    starts = np.maximum.accumulate(
        np.where(np.r_[True, users[1:] != users[:-1]], np.arange(len(users)), 0)
    )
    left = left[(left - starts[left]) < max_pairs_per_user]
    forward = np.column_stack((item_positions[left], item_positions[left + 1])).astype(
        np.int64, copy=False
    )
    forward = forward[forward[:, 0] != forward[:, 1]]
    if not len(forward):
        raise ValueError("Two-tower training data has no distinct adjacent item pairs")
    pairs = np.concatenate((forward, forward[:, ::-1]), axis=0)
    return tmdb_ids, pairs


@dataclass(frozen=True)
class TwoTowerArtifact:
    output_dir: Path
    embeddings: np.ndarray
    index: faiss.Index
    tmdb_id_to_idx: dict[int, int]
    idx_to_tmdb_id: dict[int, int]
    manifest: dict[str, object]

    @classmethod
    def load(cls, output_dir: Path) -> TwoTowerArtifact:
        output_dir = output_dir.resolve()
        required = (
            "item_embeddings.npy",
            "faiss.index",
            "tmdb_id_to_idx.json",
            "manifest.json",
        )
        missing = [name for name in required if not (output_dir / name).is_file()]
        if missing:
            raise FileNotFoundError(
                f"Incomplete two-tower artifact at {output_dir}: {missing}"
            )
        manifest = json.loads(
            (output_dir / "manifest.json").read_text(encoding="utf-8")
        )
        if (
            manifest.get("model_type") != "two_tower"
            or manifest.get("id_schema_version") != "tmdb-keyed-v1"
        ):
            raise ValueError(
                f"Incompatible two-tower artifact manifest: {output_dir / 'manifest.json'}"
            )
        embeddings = np.load(output_dir / "item_embeddings.npy")
        mapping = {
            int(key): int(value)
            for key, value in json.loads(
                (output_dir / "tmdb_id_to_idx.json").read_text(encoding="utf-8")
            ).items()
        }
        index = faiss.read_index(str(output_dir / "faiss.index"))
        if len(mapping) != len(embeddings) or index.ntotal != len(embeddings):
            raise ValueError(
                "Two-tower artifact embedding, index, and ID-map sizes differ"
            )
        return cls(
            output_dir,
            embeddings,
            index,
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
        scores, positions = self.index.search(
            self.embeddings[position : position + 1], min(self.index.ntotal, top_k + 1)
        )
        return [
            (self.idx_to_tmdb_id[int(item_position)], float(score))
            for score, item_position in zip(scores[0], positions[0], strict=True)
            if int(item_position) >= 0
        ]

    def recommend(self, seed_tmdb_ids: Iterable[int], top_k: int) -> list[int]:
        evidence = collect_seed_candidates(
            seed_tmdb_ids,
            retrieve_one=self.retrieve_one,
            source="two_tower",
            top_k=max(top_k, int(self.manifest["per_seed_candidates"])),
        )
        return order_candidate_ids(evidence)[:top_k]


def _fit_embeddings(
    pairs: np.ndarray,
    item_count: int,
    *,
    embedding_dim: int,
    batch_size: int,
    epochs: int,
    learning_rate: float,
    random_seed: int,
    progress_callback: Callable[[int, str], None] | None,
) -> np.ndarray:
    torch.manual_seed(random_seed)
    rng = np.random.default_rng(random_seed)
    query = nn.Embedding(item_count, embedding_dim)
    candidate = nn.Embedding(item_count, embedding_dim)
    optimizer = torch.optim.AdamW(
        (*query.parameters(), *candidate.parameters()), lr=learning_rate
    )
    counts = np.bincount(pairs[:, 1], minlength=item_count).astype(np.float64)
    probabilities = np.power(counts, 0.75)
    probabilities /= probabilities.sum()
    for epoch in range(epochs):
        order = rng.permutation(len(pairs))
        for start in range(0, len(pairs), batch_size):
            batch = pairs[order[start : start + batch_size]]
            source = torch.from_numpy(batch[:, 0])
            positive = torch.from_numpy(batch[:, 1])
            negative_values = rng.choice(item_count, size=len(batch), p=probabilities)
            collisions = negative_values == batch[:, 1]
            while collisions.any():
                negative_values[collisions] = rng.choice(
                    item_count, size=int(collisions.sum()), p=probabilities
                )
                collisions = negative_values == batch[:, 1]
            negative = torch.from_numpy(negative_values.astype(np.int64, copy=False))
            source_vectors = functional.normalize(query(source), dim=1)
            positive_vectors = functional.normalize(candidate(positive), dim=1)
            negative_vectors = functional.normalize(candidate(negative), dim=1)
            loss = -functional.logsigmoid(
                (source_vectors * positive_vectors).sum(dim=1)
                - (source_vectors * negative_vectors).sum(dim=1)
            ).mean()
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            optimizer.step()
        if progress_callback is not None:
            progress_callback(4 + epoch, f"fit epoch {epoch + 1}/{epochs}")
    embeddings = (
        (query.weight.detach() + candidate.weight.detach())
        .cpu()
        .numpy()
        .astype(np.float32)
    )
    faiss.normalize_L2(embeddings)
    return embeddings


def train_two_tower(
    train_path: Path,
    output_dir: Path,
    *,
    embedding_dim: int,
    batch_size: int,
    epochs: int,
    learning_rate: float,
    max_pairs_per_user: int,
    random_seed: int,
    dataset_version: str,
    per_seed_candidates: int,
    progress_callback: Callable[[int, str], None] | None = None,
    training_metadata: dict[str, object] | None = None,
) -> TwoTowerArtifact:
    """Train on chronological train interactions and publish an immutable artifact."""
    if output_dir.exists():
        raise FileExistsError(
            f"Refusing to overwrite immutable artifact directory: {output_dir}"
        )
    if not dataset_version:
        raise ValueError("dataset_version must be non-empty")

    def report(completed: int, stage: str) -> None:
        if progress_callback is not None:
            progress_callback(completed, stage)

    tmdb_ids, pairs = _load_pairs(train_path, max_pairs_per_user)
    report(1, "read and order train interactions")
    report(2, "build chronological item pairs")
    report(3, "initialize two-tower model")
    embeddings = _fit_embeddings(
        pairs,
        len(tmdb_ids),
        embedding_dim=embedding_dim,
        batch_size=batch_size,
        epochs=epochs,
        learning_rate=learning_rate,
        random_seed=random_seed,
        progress_callback=progress_callback,
    )
    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)
    report(4 + epochs, "build FAISS index")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_dir.parent / f".{output_dir.name}.tmp"
    temporary.mkdir()
    try:
        np.save(temporary / "item_embeddings.npy", embeddings)
        faiss.write_index(index, str(temporary / "faiss.index"))
        mapping = {
            str(int(tmdb_id)): position for position, tmdb_id in enumerate(tmdb_ids)
        }
        (temporary / "tmdb_id_to_idx.json").write_text(
            json.dumps(mapping, sort_keys=True), encoding="utf-8"
        )
        manifest: dict[str, object] = {
            "model_type": "two_tower",
            "id_schema_version": "tmdb-keyed-v1",
            "dataset_version": dataset_version,
            "train_sha256": _sha256(train_path),
            "embedding_dim": embedding_dim,
            "batch_size": batch_size,
            "epochs": epochs,
            "learning_rate": learning_rate,
            "max_pairs_per_user": max_pairs_per_user,
            "random_seed": random_seed,
            "per_seed_candidates": per_seed_candidates,
            "item_count": len(tmdb_ids),
            "pair_count": len(pairs),
            "pair_strategy": "adjacent_bidirectional",
            "similarity": "cosine",
        }
        if training_metadata:
            manifest.update(training_metadata)
        for filename in ("item_embeddings.npy", "faiss.index", "tmdb_id_to_idx.json"):
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
    artifact = TwoTowerArtifact.load(output_dir)
    report(5 + epochs, "verify artifact")
    return artifact
