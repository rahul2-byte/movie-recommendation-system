"""Build and verify compact, immutable runtime model bundles."""

from __future__ import annotations

import hashlib
import json
import shutil
from argparse import ArgumentParser
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import faiss
import numpy as np
import pyarrow.parquet as pq

_RETRIEVER_NAMES = ("als", "item_graph", "two_tower", "content")
_VECTOR_RETRIEVERS = frozenset({"als", "two_tower", "content"})
_ID_SCHEMA_VERSION = "tmdb-keyed-v1"
_BUNDLE_SCHEMA_VERSION = "model-bundle-v1"


class ModelBundleError(ValueError):
    """A model bundle cannot be safely served."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ModelBundleError(f"Invalid JSON: {path}") from error
    if not isinstance(value, dict):
        raise ModelBundleError(f"Expected a JSON object: {path}")
    return value


def _validate_source_artifact(name: str, path: Path) -> dict[str, Any]:
    manifest_path = path / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Missing artifact manifest: {manifest_path}")
    manifest = _read_json(manifest_path)
    expected_model_type = "lightgbm_lambdarank" if name == "ranker" else name
    if manifest.get("model_type") != expected_model_type:
        raise ModelBundleError(
            f"{name} manifest has model_type={manifest.get('model_type')!r}"
        )
    if manifest.get("dataset_version") in (None, ""):
        raise ModelBundleError(f"{name} manifest has no dataset_version")
    if name != "ranker" and manifest.get("id_schema_version") != _ID_SCHEMA_VERSION:
        raise ModelBundleError(f"{name} manifest has incompatible ID schema")
    return manifest


def _tmdb_ids_from_mapping(mapping_path: Path) -> np.ndarray:
    mapping = {int(key): int(value) for key, value in _read_json(mapping_path).items()}
    positions = set(mapping.values())
    expected = set(range(len(mapping)))
    if positions != expected:
        raise ModelBundleError(f"TMDB position map is not contiguous: {mapping_path}")
    ids = np.empty(len(mapping), dtype=np.int64)
    for tmdb_id, position in mapping.items():
        if tmdb_id <= 0:
            raise ModelBundleError(f"TMDB ID map contains invalid ID: {mapping_path}")
        ids[position] = tmdb_id
    return ids


def _copy(path: Path, destination: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"Required model artifact file is missing: {path}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, destination)


def _collect_hashes(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): _sha256(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _write_popularity_counts(train_path: Path, destination: Path) -> None:
    counts: dict[int, int] = {}
    source = pq.ParquetFile(train_path)
    if "tmdb_id" not in source.schema_arrow.names:
        raise ValueError(f"Popularity input has no tmdb_id column: {train_path}")
    for batch in source.iter_batches(columns=["tmdb_id"], batch_size=250_000):
        for tmdb_id in batch.column(0).to_numpy(zero_copy_only=False):
            item_id = int(tmdb_id)
            if item_id > 0:
                counts[item_id] = counts.get(item_id, 0) + 1
    if not counts:
        raise ValueError(f"Popularity input has no valid TMDB IDs: {train_path}")
    ids = np.asarray(sorted(counts), dtype=np.int64)
    np.savez_compressed(
        destination,
        tmdb_ids=ids,
        counts=np.asarray([counts[int(item_id)] for item_id in ids], dtype=np.float32),
    )


def build_model_bundle(
    source_artifacts: dict[str, Path],
    output_dir: Path,
    *,
    popularity_train_path: Path | None = None,
    candidate_limit: int = 300,
    rrf_rank_constant: int = 60,
) -> Path:
    """Build one immutable runtime bundle without duplicate FAISS embeddings."""
    required = {*_RETRIEVER_NAMES, "ranker"}
    if set(source_artifacts) != required:
        raise ValueError(f"Expected bundle components {sorted(required)}")
    if candidate_limit < 1 or rrf_rank_constant < 1:
        raise ValueError(
            "Bundle candidate_limit and rrf_rank_constant must be positive"
        )
    output_dir = output_dir.resolve()
    if output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite immutable bundle: {output_dir}")

    manifests = {
        name: _validate_source_artifact(name, path.resolve())
        for name, path in source_artifacts.items()
    }
    dataset_versions = {
        str(manifest["dataset_version"]) for manifest in manifests.values()
    }
    if len(dataset_versions) != 1:
        raise ModelBundleError("All model artifacts must use the same dataset_version")

    temporary = output_dir.parent / f".{output_dir.name}.tmp"
    if temporary.exists():
        raise FileExistsError(f"Temporary bundle directory already exists: {temporary}")
    temporary.mkdir(parents=True)
    try:
        for name in _RETRIEVER_NAMES:
            source = source_artifacts[name].resolve()
            destination = temporary / "retrievers" / name
            _copy(source / "manifest.json", destination / "manifest.json")
            np.save(
                destination / "tmdb_ids.npy",
                _tmdb_ids_from_mapping(source / "tmdb_id_to_idx.json"),
            )
            if name in _VECTOR_RETRIEVERS:
                _copy(source / "faiss.index", destination / "faiss.index")
            else:
                _copy(
                    source / "neighbor_positions.npy",
                    destination / "neighbor_positions.npy",
                )
            if name == "content":
                _copy(source / "vectorizer.joblib", destination / "vectorizer.joblib")
                _copy(source / "svd.joblib", destination / "svd.joblib")

        ranker_source = source_artifacts["ranker"].resolve()
        for filename in ("manifest.json", "model.txt", "feature_schema.json"):
            _copy(ranker_source / filename, temporary / "ranker" / filename)
        if popularity_train_path is not None:
            train_path = popularity_train_path.resolve()
            if not train_path.is_file():
                raise FileNotFoundError(f"Popularity input is missing: {train_path}")
            _write_popularity_counts(
                train_path, temporary / "ranker" / "popularity_counts.npz"
            )

        root_manifest = {
            "schema_version": _BUNDLE_SCHEMA_VERSION,
            "dataset_version": dataset_versions.pop(),
            "id_schema_version": _ID_SCHEMA_VERSION,
            "candidate_limit": candidate_limit,
            "rrf_rank_constant": rrf_rank_constant,
            "components": {
                name: {
                    "model_type": manifests[name]["model_type"],
                    "source_manifest_sha256": _sha256(
                        source_artifacts[name].resolve() / "manifest.json"
                    ),
                }
                for name in (*_RETRIEVER_NAMES, "ranker")
            },
            "files": _collect_hashes(temporary),
        }
        (temporary / "bundle_manifest.json").write_text(
            json.dumps(root_manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(output_dir)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return output_dir


@dataclass(frozen=True)
class CompactVectorRetriever:
    index: faiss.Index
    tmdb_ids: np.ndarray
    position_by_tmdb_id: dict[int, int]

    def retrieve_one(self, seed_tmdb_id: int, top_k: int) -> list[tuple[int, float]]:
        if top_k < 1:
            raise ValueError("top_k must be positive")
        position = self.position_by_tmdb_id.get(int(seed_tmdb_id))
        if position is None:
            return []
        query = np.asarray(self.index.reconstruct(position), dtype=np.float32)[None, :]
        scores, positions = self.index.search(query, min(self.index.ntotal, top_k))
        return [
            (int(self.tmdb_ids[int(result_position)]), float(score))
            for score, result_position in zip(scores[0], positions[0], strict=True)
            if int(result_position) >= 0
        ]


@dataclass(frozen=True)
class CompactItemGraphRetriever:
    neighbor_positions: np.ndarray
    tmdb_ids: np.ndarray
    position_by_tmdb_id: dict[int, int]

    def retrieve_one(self, seed_tmdb_id: int, top_k: int) -> list[tuple[int, float]]:
        if top_k < 1:
            raise ValueError("top_k must be positive")
        position = self.position_by_tmdb_id.get(int(seed_tmdb_id))
        if position is None:
            return []
        return [
            (int(self.tmdb_ids[int(neighbor)]), 1.0 / rank)
            for rank, neighbor in enumerate(self.neighbor_positions[position], start=1)
            if int(neighbor) >= 0
        ][:top_k]


@dataclass(frozen=True)
class ModelBundle:
    root: Path
    manifest: dict[str, Any]
    vector_retrievers: dict[str, CompactVectorRetriever]
    item_graph: CompactItemGraphRetriever

    def vector_retriever(self, name: str) -> CompactVectorRetriever:
        try:
            return self.vector_retrievers[name]
        except KeyError as error:
            raise ModelBundleError(f"Unknown vector retriever: {name}") from error


def _load_tmdb_ids(
    path: Path, expected_count: int
) -> tuple[np.ndarray, dict[int, int]]:
    ids = np.load(path, allow_pickle=False)
    if ids.ndim != 1 or len(ids) != expected_count or np.any(ids <= 0):
        raise ModelBundleError(f"Invalid TMDB ID array: {path}")
    mapping = {int(tmdb_id): position for position, tmdb_id in enumerate(ids)}
    if len(mapping) != len(ids):
        raise ModelBundleError(f"TMDB ID array contains duplicates: {path}")
    return ids.astype(np.int64, copy=False), mapping


def load_model_bundle(root: Path | str) -> ModelBundle:
    """Verify a bundle before serving any request and load compact retrieval state."""
    root = Path(root).resolve()
    manifest_path = root / "bundle_manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Model bundle manifest is missing: {manifest_path}")
    manifest = _read_json(manifest_path)
    if manifest.get("schema_version") != _BUNDLE_SCHEMA_VERSION:
        raise ModelBundleError("Unsupported model bundle schema")
    if manifest.get("id_schema_version") != _ID_SCHEMA_VERSION:
        raise ModelBundleError("Model bundle has incompatible TMDB ID schema")
    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise ModelBundleError("Model bundle has no payload hashes")
    for relative_path, expected_hash in files.items():
        payload = root / relative_path
        if not payload.is_file():
            raise ModelBundleError(f"Model bundle payload is missing: {relative_path}")
        if _sha256(payload) != expected_hash:
            raise ModelBundleError(
                f"Model bundle payload hash mismatch: {relative_path}"
            )

    vector_retrievers: dict[str, CompactVectorRetriever] = {}
    for name in _VECTOR_RETRIEVERS:
        component = root / "retrievers" / name
        source_manifest = _validate_source_artifact(name, component)
        if source_manifest["dataset_version"] != manifest.get("dataset_version"):
            raise ModelBundleError(f"{name} uses a different dataset_version")
        index = faiss.read_index(str(component / "faiss.index"))
        ids, positions = _load_tmdb_ids(component / "tmdb_ids.npy", index.ntotal)
        vector_retrievers[name] = CompactVectorRetriever(index, ids, positions)

    graph_dir = root / "retrievers" / "item_graph"
    graph_manifest = _validate_source_artifact("item_graph", graph_dir)
    if graph_manifest["dataset_version"] != manifest.get("dataset_version"):
        raise ModelBundleError("item_graph uses a different dataset_version")
    neighbors = np.load(graph_dir / "neighbor_positions.npy", allow_pickle=False)
    if neighbors.ndim != 2:
        raise ModelBundleError("Item graph neighbors must be a matrix")
    graph_ids, graph_positions = _load_tmdb_ids(
        graph_dir / "tmdb_ids.npy", len(neighbors)
    )

    ranker_manifest = _validate_source_artifact("ranker", root / "ranker")
    feature_schema = _read_json(root / "ranker" / "feature_schema.json")
    if ranker_manifest["dataset_version"] != manifest.get("dataset_version"):
        raise ModelBundleError("Ranker uses a different dataset_version")
    if ranker_manifest.get("feature_schema_version") != feature_schema.get(
        "schema_version"
    ):
        raise ModelBundleError("Ranker feature schema version is incompatible")

    return ModelBundle(
        root=root,
        manifest=manifest,
        vector_retrievers=vector_retrievers,
        item_graph=CompactItemGraphRetriever(neighbors, graph_ids, graph_positions),
    )


def main() -> None:
    parser = ArgumentParser(description="Build one immutable runtime model bundle.")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--popularity-train-path", type=Path, required=True)
    parser.add_argument("--candidate-limit", type=int, default=300)
    parser.add_argument("--rrf-rank-constant", type=int, default=60)
    for name in (*_RETRIEVER_NAMES, "ranker"):
        parser.add_argument(
            f"--{name.replace('_', '-')}-artifact", type=Path, required=True
        )
    args = parser.parse_args()
    sources = {
        name: getattr(args, f"{name}_artifact")
        for name in (*_RETRIEVER_NAMES, "ranker")
    }
    bundle_dir = build_model_bundle(
        sources,
        args.output_dir,
        popularity_train_path=args.popularity_train_path,
        candidate_limit=args.candidate_limit,
        rrf_rank_constant=args.rrf_rank_constant,
    )
    print(json.dumps(load_model_bundle(bundle_dir).manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
