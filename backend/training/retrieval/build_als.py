"""Authoritative local training for TMDB-keyed implicit ALS artifacts."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

import faiss
import numpy as np
import pyarrow.parquet as pq
import yaml
from implicit.cpu.als import AlternatingLeastSquares
from retrieval.seeded import collect_seed_candidates, order_candidate_ids
from scipy.sparse import coo_matrix, csr_matrix
from threadpoolctl import threadpool_limits


@dataclass(frozen=True)
class AlsTrainingConfig:
    """Validated hyperparameters and paths for one ALS training run."""
    dataset_version: str
    output_dir: Path
    factors: int
    regularization: float
    alpha: float
    iterations: int
    num_threads: int
    random_seed: int
    per_seed_candidates: int
    parquet_batch_size: int
    mlflow_experiment_name: str


def load_als_training_config(path: Path) -> AlsTrainingConfig:
    """Load and validate the ALS section of the retrieval config."""
    path = path.resolve()
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    values = payload.get("als") if isinstance(payload, dict) else None
    if not isinstance(values, dict):
        raise ValueError("retrieval training configuration must contain an als mapping")
    required = (
        "dataset_version",
        "output_dir",
        "factors",
        "regularization",
        "alpha",
        "iterations",
        "num_threads",
        "random_seed",
        "per_seed_candidates",
        "parquet_batch_size",
        "mlflow_experiment_name",
    )
    missing = [key for key in required if key not in values]
    if missing:
        raise ValueError(f"als configuration is missing values: {missing}")
    positive_ints = (
        "factors",
        "iterations",
        "per_seed_candidates",
        "parquet_batch_size",
    )
    if any(
        not isinstance(values[key], int) or values[key] < 1 for key in positive_ints
    ):
        raise ValueError(
            f"als.{', als.'.join(positive_ints)} must be positive integers"
        )
    if not isinstance(values["num_threads"], int) or values["num_threads"] < 0:
        raise ValueError("als.num_threads must be zero or a positive integer")
    if not isinstance(values["random_seed"], int):
        raise ValueError("als.random_seed must be an integer")
    for key in ("regularization", "alpha"):
        if not isinstance(values[key], (int, float)) or values[key] <= 0:
            raise ValueError(f"als.{key} must be positive")
    if not isinstance(values["dataset_version"], str) or not values["dataset_version"]:
        raise ValueError("als.dataset_version must be a non-empty string")
    if not isinstance(values["output_dir"], str) or not values["output_dir"]:
        raise ValueError("als.output_dir must be a non-empty path")
    if (
        not isinstance(values["mlflow_experiment_name"], str)
        or not values["mlflow_experiment_name"]
    ):
        raise ValueError("als.mlflow_experiment_name must be a non-empty string")
    return AlsTrainingConfig(
        dataset_version=values["dataset_version"],
        output_dir=(path.parent / values["output_dir"]).resolve(),
        factors=values["factors"],
        regularization=float(values["regularization"]),
        alpha=float(values["alpha"]),
        iterations=values["iterations"],
        num_threads=values["num_threads"],
        random_seed=values["random_seed"],
        per_seed_candidates=values["per_seed_candidates"],
        parquet_batch_size=values["parquet_batch_size"],
        mlflow_experiment_name=values["mlflow_experiment_name"],
    )


def _sha256(path: Path) -> str:
    """Hash a training input for artifact reproducibility metadata."""
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_interactions(
    path: Path, batch_size: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Read required interaction columns in bounded parquet batches."""
    source = pq.ParquetFile(path)
    columns = ("user_id", "tmdb_id", "rating")
    missing = set(columns) - set(source.schema_arrow.names)
    if missing:
        raise ValueError(f"ALS training data is missing columns: {sorted(missing)}")
    users: list[np.ndarray] = []
    items: list[np.ndarray] = []
    ratings: list[np.ndarray] = []
    for batch in source.iter_batches(columns=columns, batch_size=batch_size):
        users.append(batch.column(0).to_numpy(zero_copy_only=False).astype(np.int64))
        items.append(batch.column(1).to_numpy(zero_copy_only=False).astype(np.int64))
        ratings.append(
            batch.column(2).to_numpy(zero_copy_only=False).astype(np.float32)
        )
    if not users:
        raise ValueError("ALS training data has no interactions")
    return np.concatenate(users), np.concatenate(items), np.concatenate(ratings)


def _build_user_items(
    users: np.ndarray, items: np.ndarray, ratings: np.ndarray
) -> tuple[csr_matrix, np.ndarray, np.ndarray]:
    """Build the sparse user-item matrix consumed by implicit ALS."""
    if np.any(users <= 0) or np.any(items <= 0) or np.any(~np.isfinite(ratings)):
        raise ValueError(
            "ALS interactions contain invalid user, item, or rating values"
        )
    unique_users, user_rows = np.unique(users, return_inverse=True)
    unique_items, item_columns = np.unique(items, return_inverse=True)
    matrix = coo_matrix(
        (ratings, (user_rows, item_columns)),
        shape=(len(unique_users), len(unique_items)),
        dtype=np.float32,
    ).tocsr()
    matrix.sum_duplicates()
    matrix.sort_indices()
    return matrix, unique_users, unique_items


@dataclass(frozen=True)
class AlsArtifact:
    """Trained ALS embeddings, FAISS index, mappings, and manifest."""
    output_dir: Path
    embeddings: np.ndarray
    index: faiss.Index
    tmdb_id_to_idx: dict[int, int]
    idx_to_tmdb_id: dict[int, int]
    manifest: dict[str, object]

    @classmethod
    def load(cls, output_dir: Path) -> AlsArtifact:
        """Load and validate serialized ALS state."""
        """Load and validate an immutable ALS artifact directory."""
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
                f"Incomplete ALS artifact at {output_dir}: {missing}"
            )
        manifest = json.loads(
            (output_dir / "manifest.json").read_text(encoding="utf-8")
        )
        if (
            manifest.get("model_type") != "als"
            or manifest.get("id_schema_version") != "tmdb-keyed-v1"
        ):
            raise ValueError(
                f"Incompatible ALS artifact manifest: {output_dir / 'manifest.json'}"
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
            raise ValueError("ALS artifact embedding, index, and ID-map sizes differ")
        return cls(
            output_dir=output_dir,
            embeddings=embeddings,
            index=index,
            tmdb_id_to_idx=mapping,
            idx_to_tmdb_id={position: tmdb_id for tmdb_id, position in mapping.items()},
            manifest=manifest,
        )

    def retrieve_one(self, seed_tmdb_id: int, top_k: int) -> list[tuple[int, float]]:
        """Retrieve nearest ALS items for one seed movie."""
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
        """Fuse per-seed ALS candidates into a deterministic list."""
        per_seed_candidates = max(top_k, int(self.manifest["per_seed_candidates"]))
        evidence = collect_seed_candidates(
            seed_tmdb_ids,
            retrieve_one=self.retrieve_one,
            source="als",
            top_k=per_seed_candidates,
        )
        return order_candidate_ids(evidence)[:top_k]


def train_als(
    train_path: Path,
    output_dir: Path,
    *,
    factors: int,
    regularization: float,
    alpha: float,
    iterations: int,
    num_threads: int,
    random_seed: int,
    dataset_version: str,
    per_seed_candidates: int,
    parquet_batch_size: int,
    progress_callback: Callable[[int, str], None] | None = None,
    training_metadata: dict[str, object] | None = None,
) -> AlsArtifact:
    """Train and atomically publish one immutable TMDB-keyed ALS artifact."""
    if output_dir.exists():
        raise FileExistsError(
            f"Refusing to overwrite immutable artifact directory: {output_dir}"
        )
    if not dataset_version:
        raise ValueError("dataset_version must be non-empty")

    def report(completed: int, stage: str) -> None:
        """Report training progress for the requested stage."""
        if progress_callback is not None:
            progress_callback(completed, stage)

    users, items, ratings = _load_interactions(train_path, parquet_batch_size)
    report(1, "read train interactions")
    user_items, user_ids, tmdb_ids = _build_user_items(users, items, ratings)
    del users, items, ratings
    report(2, "build sparse user-item matrix")
    with threadpool_limits(limits=1, user_api="blas"):
        model = AlternatingLeastSquares(
            factors=factors,
            regularization=regularization,
            alpha=alpha,
            iterations=iterations,
            num_threads=num_threads,
            random_state=random_seed,
            calculate_training_loss=False,
        )
        model.fit(user_items, show_progress=False)
    report(3, "fit ALS")
    embeddings = model.item_factors.astype(np.float32, copy=False)
    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)
    report(4, "build FAISS index")
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
            "model_type": "als",
            "id_schema_version": "tmdb-keyed-v1",
            "dataset_version": dataset_version,
            "train_sha256": _sha256(train_path),
            "factors": factors,
            "regularization": regularization,
            "alpha": alpha,
            "iterations": iterations,
            "num_threads": num_threads,
            "random_seed": random_seed,
            "per_seed_candidates": per_seed_candidates,
            "user_count": len(user_ids),
            "item_count": len(tmdb_ids),
            "interaction_count": int(user_items.nnz),
            "similarity": "inner_product",
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
    artifact = AlsArtifact.load(output_dir)
    report(5, "verify artifact")
    return artifact
