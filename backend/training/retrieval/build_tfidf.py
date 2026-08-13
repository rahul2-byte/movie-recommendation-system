"""Authoritative local training for TMDB-keyed TF-IDF retrieval artifacts."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

import faiss
import joblib
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import yaml
from retrieval.seeded import collect_seed_candidates, order_candidate_ids
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer


@dataclass(frozen=True)
class TfidfTrainingConfig:
    dataset_version: str
    output_dir: Path
    text_fields: tuple[str, ...]
    field_weights: dict[str, int]
    min_df: int
    max_features: int | None
    embedding_dim: int
    random_seed: int
    per_seed_candidates: int
    mlflow_experiment_name: str


def _load_training_config(path: Path, section: str) -> TfidfTrainingConfig:
    path = path.resolve()
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    values = payload.get(section) if isinstance(payload, dict) else None
    if not isinstance(values, dict):
        raise ValueError(
            f"retrieval training configuration must contain a {section} mapping"
        )
    dataset_version = values.get("dataset_version")
    output_dir = values.get("output_dir")
    text_fields = values.get("text_fields")
    field_weights = values.get("field_weights", {})
    min_df = values.get("min_df")
    max_features = values.get("max_features")
    embedding_dim = values.get("embedding_dim")
    random_seed = values.get("random_seed")
    per_seed_candidates = values.get("per_seed_candidates")
    experiment = values.get("mlflow_experiment_name")
    if not isinstance(dataset_version, str) or not dataset_version:
        raise ValueError(f"{section}.dataset_version must be a non-empty string")
    if not isinstance(output_dir, str) or not output_dir:
        raise ValueError(f"{section}.output_dir must be a non-empty path")
    if (
        not isinstance(text_fields, list)
        or not text_fields
        or not all(isinstance(value, str) and value for value in text_fields)
    ):
        raise ValueError(f"{section}.text_fields must be a non-empty list of strings")
    if not isinstance(field_weights, dict) or set(field_weights) - set(text_fields):
        raise ValueError(f"{section}.field_weights must map configured text fields")
    if any(
        not isinstance(weight, int) or weight < 1 for weight in field_weights.values()
    ):
        raise ValueError(f"{section}.field_weights values must be positive integers")
    if not isinstance(min_df, int) or min_df < 1:
        raise ValueError(f"{section}.min_df must be a positive integer")
    if max_features is not None and (
        not isinstance(max_features, int) or max_features < 1
    ):
        raise ValueError(f"{section}.max_features must be null or a positive integer")
    if not isinstance(embedding_dim, int) or embedding_dim < 1:
        raise ValueError(f"{section}.embedding_dim must be a positive integer")
    if not isinstance(random_seed, int):
        raise ValueError(f"{section}.random_seed must be an integer")
    if not isinstance(per_seed_candidates, int) or per_seed_candidates < 1:
        raise ValueError(f"{section}.per_seed_candidates must be a positive integer")
    if not isinstance(experiment, str) or not experiment:
        raise ValueError(f"{section}.mlflow_experiment_name must be a non-empty string")
    return TfidfTrainingConfig(
        dataset_version=dataset_version,
        output_dir=(path.parent / output_dir).resolve(),
        text_fields=tuple(text_fields),
        field_weights={
            field: int(field_weights.get(field, 1)) for field in text_fields
        },
        min_df=min_df,
        max_features=max_features,
        embedding_dim=embedding_dim,
        random_seed=random_seed,
        per_seed_candidates=per_seed_candidates,
        mlflow_experiment_name=experiment,
    )


def load_tfidf_training_config(path: Path) -> TfidfTrainingConfig:
    return _load_training_config(path, "tfidf")


def load_content_training_config(path: Path) -> TfidfTrainingConfig:
    return _load_training_config(path, "content")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _text(value: object) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return ""
    if isinstance(value, (list, tuple, np.ndarray)):
        return " ".join(str(part) for part in value if part)
    return str(value)


def _structured_token(field: str, value: object) -> str:
    normalized = "".join(
        character if character.isalnum() else "_" for character in str(value).lower()
    ).strip("_")
    return f"{field}_{normalized}" if normalized else ""


def _field_text(field: str, value: object) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return ""
    if field == "release_year" and value is not None and not pd.isna(value):
        year = int(float(value))
        return f"year_{year} decade_{year // 10 * 10}"
    if field == "runtime_minutes" and value is not None and not pd.isna(value):
        return f"runtime_{int(float(value)) // 15 * 15}"
    if field in {"genres", "keywords", "top_cast"}:
        values = value if isinstance(value, (list, tuple, np.ndarray)) else [value]
        return " ".join(_structured_token(field, item) for item in values if item)
    if field in {"director", "collection_name", "language", "country"}:
        return _structured_token(field, value)
    return _text(value)


def _catalog_text(
    catalog: pd.DataFrame, fields: tuple[str, ...], field_weights: dict[str, int]
) -> list[str]:
    missing = set(fields) - set(catalog.columns)
    if missing:
        raise ValueError(f"Catalog is missing TF-IDF fields: {sorted(missing)}")
    text = catalog.loc[:, list(fields)].apply(
        lambda row: " ".join(
            " ".join([_field_text(field, row[field])] * field_weights[field])
            for field in fields
            if _field_text(field, row[field])
        ),
        axis=1,
    )
    if not text.str.strip().any():
        raise ValueError("Configured TF-IDF fields contain no usable text")
    return text.tolist()


@dataclass(frozen=True)
class TfidfArtifact:
    output_dir: Path
    vectorizer: TfidfVectorizer
    svd: TruncatedSVD
    embeddings: np.ndarray
    index: faiss.Index
    tmdb_id_to_idx: dict[int, int]
    idx_to_tmdb_id: dict[int, int]
    manifest: dict[str, object]

    @classmethod
    def load(cls, output_dir: Path) -> TfidfArtifact:
        output_dir = output_dir.resolve()
        manifest_path = output_dir / "manifest.json"
        required = (
            "vectorizer.joblib",
            "svd.joblib",
            "item_embeddings.npy",
            "faiss.index",
            "tmdb_id_to_idx.json",
            "manifest.json",
        )
        missing = [name for name in required if not (output_dir / name).is_file()]
        if missing:
            raise FileNotFoundError(
                f"Incomplete TF-IDF artifact at {output_dir}: {missing}"
            )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if (
            manifest.get("model_type") not in {"tfidf", "content"}
            or manifest.get("id_schema_version") != "tmdb-keyed-v1"
        ):
            raise ValueError(f"Incompatible TF-IDF artifact manifest: {manifest_path}")
        embeddings = np.load(output_dir / "item_embeddings.npy")
        id_map = {
            int(key): int(value)
            for key, value in json.loads(
                (output_dir / "tmdb_id_to_idx.json").read_text(encoding="utf-8")
            ).items()
        }
        index = faiss.read_index(str(output_dir / "faiss.index"))
        if len(id_map) != len(embeddings) or index.ntotal != len(embeddings):
            raise ValueError(
                "TF-IDF artifact embedding, index, and ID-map sizes differ"
            )
        return cls(
            output_dir,
            joblib.load(output_dir / "vectorizer.joblib"),
            joblib.load(output_dir / "svd.joblib"),
            embeddings,
            index,
            id_map,
            {value: key for key, value in id_map.items()},
            manifest,
        )

    def retrieve_one(self, seed_tmdb_id: int, top_k: int) -> list[tuple[int, float]]:
        if top_k < 1:
            raise ValueError("top_k must be positive")
        index = self.tmdb_id_to_idx.get(int(seed_tmdb_id))
        if index is None:
            return []
        distances, indices = self.index.search(
            self.embeddings[index : index + 1], min(self.index.ntotal, top_k + 1)
        )
        return [
            (self.idx_to_tmdb_id[int(item_index)], float(score))
            for score, item_index in zip(distances[0], indices[0], strict=True)
            if int(item_index) >= 0
        ]

    def recommend(self, seed_tmdb_ids: Iterable[int], top_k: int) -> list[int]:
        per_seed_candidates = max(
            top_k, int(self.manifest.get("per_seed_candidates", top_k))
        )
        seeds = list(
            dict.fromkeys(int(seed_id) for seed_id in seed_tmdb_ids if int(seed_id) > 0)
        )
        known = [
            (seed_id, self.tmdb_id_to_idx[seed_id])
            for seed_id in seeds
            if seed_id in self.tmdb_id_to_idx
        ]
        neighbors: dict[int, list[tuple[int, float]]] = {}
        if known:
            distances, indices = self.index.search(
                self.embeddings[[position for _, position in known]],
                min(self.index.ntotal, per_seed_candidates + 1),
            )
            neighbors = {
                seed_id: [
                    (self.idx_to_tmdb_id[int(item_index)], float(score))
                    for score, item_index in zip(
                        seed_distances, seed_indices, strict=True
                    )
                    if int(item_index) >= 0
                ]
                for (seed_id, _), seed_distances, seed_indices in zip(
                    known, distances, indices, strict=True
                )
            }
        evidence = collect_seed_candidates(
            seeds,
            retrieve_one=lambda seed_id, _: neighbors.get(seed_id, []),
            source=str(self.manifest.get("model_type", "tfidf")),
            top_k=per_seed_candidates,
        )
        return order_candidate_ids(evidence)[:top_k]


def _seed_ids(seed_tmdb_ids: Iterable[int]) -> list[int]:
    return list(
        dict.fromkeys(int(seed_id) for seed_id in seed_tmdb_ids if int(seed_id) > 0)
    )


def _merge_neighbor_rows(
    seed_ids: list[int], neighbor_ids: np.ndarray, top_k: int
) -> list[int]:
    """Match seed-wise support and rank ordering without Python candidate objects."""
    candidates: list[np.ndarray] = []
    ranks: list[np.ndarray] = []
    forbidden = np.asarray(seed_ids, dtype=np.int64)
    for row in neighbor_ids:
        valid = row[(row > 0) & ~np.isin(row, forbidden)]
        if not len(valid):
            continue
        _, first_positions = np.unique(valid, return_index=True)
        valid = valid[np.sort(first_positions)][:top_k]
        candidates.append(valid)
        ranks.append(np.arange(1, len(valid) + 1, dtype=np.int32))
    if not candidates:
        return []
    candidate_ids = np.concatenate(candidates)
    candidate_ranks = np.concatenate(ranks)
    unique_ids, inverse = np.unique(candidate_ids, return_inverse=True)
    support = np.zeros(len(unique_ids), dtype=np.int16)
    np.add.at(support, inverse, 1)
    best_rank = np.full(len(unique_ids), np.iinfo(np.int32).max, dtype=np.int32)
    np.minimum.at(best_rank, inverse, candidate_ranks)
    order = np.lexsort((unique_ids, best_rank, -support))
    return unique_ids[order[:top_k]].astype(int).tolist()


@dataclass(frozen=True)
class ExactSeedCache:
    """Exact per-seed neighbors reused during one offline evaluation run."""

    artifact: TfidfArtifact
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


def build_exact_seed_cache(
    artifact: TfidfArtifact,
    queries_path: Path,
    *,
    query_limit: int | None = None,
    batch_size: int = 512,
    progress_callback: Callable[[int, int], None] | None = None,
) -> ExactSeedCache:
    """Build an exact, bounded-memory cache of neighbors for evaluation seeds."""
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    source = pq.ParquetFile(queries_path)
    if "seed_tmdb_ids" not in source.schema_arrow.names:
        raise ValueError("Query data is missing seed_tmdb_ids")
    remaining = query_limit
    parts: list[np.ndarray] = []
    for batch in source.iter_batches(columns=["seed_tmdb_ids"], batch_size=5_000):
        if remaining is not None and remaining == 0:
            break
        current = batch.slice(0, remaining) if remaining is not None else batch
        values = current.column(0).flatten().to_numpy(zero_copy_only=False)
        if len(values):
            parts.append(np.asarray(values, dtype=np.int64))
        if remaining is not None:
            remaining -= current.num_rows
    values = np.concatenate(parts) if parts else np.empty(0, dtype=np.int64)
    unique_seed_ids = np.unique(values[values > 0])
    known_seed_ids = np.asarray(
        [
            seed_id
            for seed_id in unique_seed_ids
            if int(seed_id) in artifact.tmdb_id_to_idx
        ],
        dtype=np.int64,
    )
    candidate_count = min(
        artifact.index.ntotal,
        int(artifact.manifest.get("per_seed_candidates", 200)) + 1,
    )
    neighbor_ids = np.zeros((len(known_seed_ids), candidate_count), dtype=np.int64)
    item_ids = np.asarray(
        [
            artifact.idx_to_tmdb_id[position]
            for position in range(len(artifact.embeddings))
        ],
        dtype=np.int64,
    )
    if progress_callback is not None:
        progress_callback(0, len(known_seed_ids))
    for start in range(0, len(known_seed_ids), batch_size):
        stop = min(start + batch_size, len(known_seed_ids))
        positions = np.asarray(
            [
                artifact.tmdb_id_to_idx[int(seed_id)]
                for seed_id in known_seed_ids[start:stop]
            ],
            dtype=np.int64,
        )
        _, indices = artifact.index.search(
            artifact.embeddings[positions], candidate_count
        )
        valid = indices >= 0
        current_neighbors = neighbor_ids[start:stop]
        current_neighbors[valid] = item_ids[indices[valid]]
        if progress_callback is not None:
            progress_callback(stop, len(known_seed_ids))
    return ExactSeedCache(
        artifact=artifact,
        row_by_seed={
            int(seed_id): position for position, seed_id in enumerate(known_seed_ids)
        },
        neighbor_ids=neighbor_ids,
    )


def build_tfidf_seed_cache(
    artifact: TfidfArtifact,
    queries_path: Path,
    *,
    query_limit: int | None = None,
    batch_size: int = 512,
    progress_callback: Callable[[int, int], None] | None = None,
) -> ExactSeedCache:
    """Compatibility name for the generic exact seed-neighbor cache."""
    return build_exact_seed_cache(
        artifact,
        queries_path,
        query_limit=query_limit,
        batch_size=batch_size,
        progress_callback=progress_callback,
    )


def train_tfidf(
    catalog_path: Path,
    output_dir: Path,
    *,
    text_fields: tuple[str, ...],
    field_weights: dict[str, int] | None = None,
    min_df: int,
    max_features: int | None,
    embedding_dim: int,
    random_seed: int,
    dataset_version: str,
    model_type: str = "tfidf",
    training_metadata: dict[str, object] | None = None,
    progress_callback: Callable[[int, str], None] | None = None,
) -> TfidfArtifact:
    """Train and atomically publish one immutable TMDB-keyed TF-IDF artifact."""
    if model_type not in {"tfidf", "content"}:
        raise ValueError("model_type must be tfidf or content")
    if min_df < 1:
        raise ValueError("min_df must be positive")
    if embedding_dim < 1:
        raise ValueError("embedding_dim must be positive")
    if not dataset_version:
        raise ValueError("dataset_version must be non-empty")
    output_dir = output_dir.resolve()
    if output_dir.exists():
        raise FileExistsError(
            f"Refusing to overwrite immutable artifact directory: {output_dir}"
        )

    def report(completed: int, stage: str) -> None:
        if progress_callback is not None:
            progress_callback(completed, stage)

    catalog = pd.read_parquet(catalog_path)
    report(1, "read catalog")
    if catalog["tmdb_id"].isna().any() or catalog["tmdb_id"].duplicated().any():
        raise ValueError("Catalog must contain unique, non-null tmdb_id values")
    normalized_weights = {
        field: int((field_weights or {}).get(field, 1)) for field in text_fields
    }
    if any(weight < 1 for weight in normalized_weights.values()):
        raise ValueError("field_weights must be positive")
    documents = _catalog_text(catalog, text_fields, normalized_weights)
    report(2, "build documents")
    vectorizer = TfidfVectorizer(
        dtype=np.float32, min_df=min_df, max_features=max_features
    )
    sparse_embeddings = vectorizer.fit_transform(documents)
    report(3, "fit TF-IDF")
    maximum_components = min(sparse_embeddings.shape) - 1
    if maximum_components < 1:
        raise ValueError("TF-IDF matrix is too small for dimensionality reduction")
    svd = TruncatedSVD(
        n_components=min(embedding_dim, maximum_components), random_state=random_seed
    )
    embeddings = svd.fit_transform(sparse_embeddings).astype(np.float32, copy=False)
    faiss.normalize_L2(embeddings)
    report(4, "reduce embeddings")
    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)
    report(5, "build FAISS index")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_dir.parent / f".{output_dir.name}.tmp"
    temporary.mkdir()
    try:
        joblib.dump(vectorizer, temporary / "vectorizer.joblib")
        joblib.dump(svd, temporary / "svd.joblib")
        np.save(temporary / "item_embeddings.npy", embeddings)
        faiss.write_index(index, str(temporary / "faiss.index"))
        id_map = {
            str(int(tmdb_id)): position
            for position, tmdb_id in enumerate(catalog["tmdb_id"])
        }
        (temporary / "tmdb_id_to_idx.json").write_text(
            json.dumps(id_map, sort_keys=True), encoding="utf-8"
        )
        manifest: dict[str, object] = {
            "model_type": model_type,
            "id_schema_version": "tmdb-keyed-v1",
            "dataset_version": dataset_version,
            "catalog_sha256": _sha256(catalog_path),
            "text_fields": list(text_fields),
            "field_weights": normalized_weights,
            "min_df": min_df,
            "max_features": max_features,
            "embedding_dim": int(embeddings.shape[1]),
            "random_seed": random_seed,
            "catalog_rows": len(catalog),
        }
        if training_metadata:
            manifest.update(training_metadata)
        for filename in (
            "vectorizer.joblib",
            "svd.joblib",
            "item_embeddings.npy",
            "faiss.index",
            "tmdb_id_to_idx.json",
        ):
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
    artifact = TfidfArtifact.load(output_dir)
    report(6, "verify artifact")
    return artifact
