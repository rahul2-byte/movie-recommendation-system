import json

import faiss
import joblib
import numpy as np
import pandas as pd
import pytest
from serving.model_bundle import (
    ModelBundleError,
    build_model_bundle,
    load_model_bundle,
)


def _write_vector_artifact(path, model_type: str) -> None:
    path.mkdir()
    embeddings = np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)
    index = faiss.IndexFlatIP(2)
    index.add(embeddings)
    np.save(path / "item_embeddings.npy", embeddings)
    faiss.write_index(index, str(path / "faiss.index"))
    (path / "tmdb_id_to_idx.json").write_text(
        json.dumps({"101": 0, "202": 1}), encoding="utf-8"
    )
    if model_type == "content":
        joblib.dump({"kind": "vectorizer"}, path / "vectorizer.joblib")
        joblib.dump({"kind": "svd"}, path / "svd.joblib")
    (path / "manifest.json").write_text(
        json.dumps(
            {
                "model_type": model_type,
                "dataset_version": "fixture-v1",
                "id_schema_version": "tmdb-keyed-v1",
                "per_seed_candidates": 2,
            }
        ),
        encoding="utf-8",
    )


def _write_item_graph_artifact(path) -> None:
    path.mkdir()
    np.save(path / "neighbor_positions.npy", np.array([[1], [0]], dtype=np.int32))
    (path / "tmdb_id_to_idx.json").write_text(
        json.dumps({"101": 0, "202": 1}), encoding="utf-8"
    )
    (path / "manifest.json").write_text(
        json.dumps(
            {
                "model_type": "item_graph",
                "dataset_version": "fixture-v1",
                "id_schema_version": "tmdb-keyed-v1",
                "per_seed_candidates": 2,
            }
        ),
        encoding="utf-8",
    )


def _write_ranker_artifact(path) -> None:
    path.mkdir()
    (path / "model.txt").write_text("fixture model", encoding="utf-8")
    (path / "feature_schema.json").write_text(
        json.dumps(
            {
                "schema_version": "ranking-features-v2",
                "dataset_version": "fixture-v1",
                "feature_names": ["retrieval_content_rank"],
                "defaults": {"retrieval_content_rank": 0.0},
            }
        ),
        encoding="utf-8",
    )
    (path / "manifest.json").write_text(
        json.dumps(
            {
                "model_type": "lightgbm_lambdarank",
                "dataset_version": "fixture-v1",
                "feature_schema_version": "ranking-features-v2",
            }
        ),
        encoding="utf-8",
    )


@pytest.fixture
def source_artifacts(tmp_path):
    artifacts = {}
    for name in ("als", "two_tower", "content"):
        artifact = tmp_path / name
        _write_vector_artifact(artifact, name)
        artifacts[name] = artifact
    graph = tmp_path / "item_graph"
    _write_item_graph_artifact(graph)
    artifacts["item_graph"] = graph
    ranker = tmp_path / "ranker"
    _write_ranker_artifact(ranker)
    artifacts["ranker"] = ranker
    return artifacts


def test_bundle_compacts_vector_artifacts_without_changing_neighbors(
    tmp_path, source_artifacts
):
    bundle_dir = build_model_bundle(source_artifacts, tmp_path / "bundle")

    assert not (bundle_dir / "retrievers" / "als" / "item_embeddings.npy").exists()
    assert not (bundle_dir / "retrievers" / "als" / "source_id_map.json").exists()
    assert (bundle_dir / "retrievers" / "als" / "tmdb_ids.npy").is_file()

    bundle = load_model_bundle(bundle_dir)

    assert bundle.vector_retriever("als").retrieve_one(101, 2) == [
        (101, pytest.approx(1.0)),
        (202, pytest.approx(0.0)),
    ]
    assert bundle.item_graph.retrieve_one(101, 1) == [(202, 1.0)]
    graph_positions = np.load(
        bundle_dir / "retrievers" / "item_graph" / "neighbor_positions.npy"
    )
    assert graph_positions.dtype == np.uint16


def test_bundle_loader_accepts_configured_string_path(tmp_path, source_artifacts):
    bundle_dir = build_model_bundle(source_artifacts, tmp_path / "bundle")

    assert load_model_bundle(str(bundle_dir)).root == bundle_dir.resolve()


@pytest.mark.parametrize("quantization", ["fp16", "int8", "sq6", "sq4"])
def test_bundle_quantization_variants_load_and_record_mode(
    tmp_path, source_artifacts, quantization
):
    bundle_dir = build_model_bundle(
        source_artifacts, tmp_path / quantization, quantization=quantization
    )

    manifest = json.loads((bundle_dir / "bundle_manifest.json").read_text())
    assert manifest["schema_version"] == "model-bundle-v2"
    assert manifest["quantization"] == quantization
    assert load_model_bundle(bundle_dir).vector_retriever("als").retrieve_one(101, 2)


def test_bundle_rejects_tampered_payload(tmp_path, source_artifacts):
    bundle_dir = build_model_bundle(source_artifacts, tmp_path / "bundle")
    (bundle_dir / "retrievers" / "als" / "faiss.index").write_bytes(b"tampered")

    with pytest.raises(ModelBundleError, match="hash"):
        load_model_bundle(bundle_dir)


def test_bundle_output_is_immutable(tmp_path, source_artifacts):
    output_dir = tmp_path / "bundle"
    build_model_bundle(source_artifacts, output_dir)

    with pytest.raises(FileExistsError, match="immutable"):
        build_model_bundle(source_artifacts, output_dir)


def test_bundle_includes_ranker_popularity_feature_state(tmp_path, source_artifacts):
    train_path = tmp_path / "train.parquet"
    pd.DataFrame({"tmdb_id": [101, 101, 202]}).to_parquet(train_path, index=False)

    bundle_dir = build_model_bundle(
        source_artifacts, tmp_path / "bundle", popularity_train_path=train_path
    )

    payload = np.load(bundle_dir / "ranker" / "popularity_counts.npz")
    assert payload["tmdb_ids"].tolist() == [101, 202]
    assert payload["counts"].tolist() == [2.0, 1.0]


def test_bundle_compacts_missing_graph_neighbors(tmp_path, source_artifacts):
    np.save(
        source_artifacts["item_graph"] / "neighbor_positions.npy",
        np.array([[1, -1], [-1, 0]], dtype=np.int32),
    )

    bundle_dir = build_model_bundle(source_artifacts, tmp_path / "bundle")

    positions = np.load(
        bundle_dir / "retrievers" / "item_graph" / "neighbor_positions.npy"
    )
    assert positions.tolist() == [[1, 65535], [65535, 0]]
    assert load_model_bundle(bundle_dir).item_graph.retrieve_one(101, 2) == [(202, 1.0)]
