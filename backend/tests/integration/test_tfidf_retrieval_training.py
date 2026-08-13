from pathlib import Path

import numpy as np
import pandas as pd
from training.retrieval.build_content_retriever import (
    TfidfArtifact,
    build_tfidf_seed_cache,
    train_tfidf,
)


def test_train_tfidf_writes_loadable_tmdb_keyed_artifact(tmp_path: Path):
    catalog_path = tmp_path / "catalog.parquet"
    pd.DataFrame(
        [
            {
                "tmdb_id": 1,
                "title": "space war",
                "overview": "space battle",
                "genres": ["science fiction"],
                "keywords": ["space"],
            },
            {
                "tmdb_id": 2,
                "title": "space rescue",
                "overview": "space mission",
                "genres": ["science fiction"],
                "keywords": ["space"],
            },
            {
                "tmdb_id": 3,
                "title": "kitchen drama",
                "overview": "family dinner",
                "genres": ["drama"],
                "keywords": ["family"],
            },
        ]
    ).to_parquet(catalog_path, index=False)

    progress: list[tuple[int, str]] = []
    artifact = train_tfidf(
        catalog_path,
        tmp_path / "artifact",
        text_fields=("title", "overview", "genres", "keywords"),
        min_df=1,
        max_features=None,
        embedding_dim=2,
        random_seed=42,
        dataset_version="fixture-v1",
        training_metadata={"per_seed_candidates": 3},
        progress_callback=lambda completed, stage: progress.append((completed, stage)),
    )

    assert artifact.manifest["dataset_version"] == "fixture-v1"
    assert artifact.manifest["per_seed_candidates"] == 3
    assert artifact.idx_to_tmdb_id == {0: 1, 1: 2, 2: 3}
    assert (tmp_path / "artifact" / "svd.joblib").is_file()
    assert artifact.recommend([1, 3], top_k=2) == [2]
    assert (tmp_path / "artifact" / "manifest.json").is_file()
    assert progress[-1] == (6, "verify artifact")


def test_train_tfidf_can_publish_a_field_weighted_content_artifact(tmp_path: Path):
    catalog_path = tmp_path / "catalog.parquet"
    pd.DataFrame(
        [
            {
                "tmdb_id": 1,
                "title": "space",
                "overview": "quiet",
                "genres": ["science fiction"],
                "release_year": 2001,
            },
            {
                "tmdb_id": 2,
                "title": "space",
                "overview": "quiet",
                "genres": ["science fiction"],
                "release_year": 2002,
            },
            {
                "tmdb_id": 3,
                "title": "family",
                "overview": "drama",
                "genres": ["drama"],
                "release_year": 1999,
            },
        ]
    ).to_parquet(catalog_path, index=False)

    artifact = train_tfidf(
        catalog_path,
        tmp_path / "content",
        text_fields=("title", "overview", "genres", "release_year"),
        field_weights={"title": 3, "overview": 1, "genres": 2, "release_year": 1},
        min_df=1,
        max_features=None,
        embedding_dim=2,
        random_seed=42,
        dataset_version="fixture-v1",
        model_type="content",
    )

    assert artifact.manifest["model_type"] == "content"
    assert artifact.manifest["field_weights"]["title"] == 3


def test_tfidf_recommendation_batches_known_seed_searches_without_pooling_them():
    class RecordingIndex:
        ntotal = 3

        def __init__(self) -> None:
            self.query_shapes: list[tuple[int, int]] = []

        def search(self, vectors: np.ndarray, count: int):
            self.query_shapes.append(vectors.shape)
            assert count == 3
            return (
                np.array([[1.0, 0.9, 0.1], [1.0, 0.8, 0.2]], dtype=np.float32),
                np.array([[0, 2, 1], [1, 2, 0]], dtype=np.int64),
            )

    index = RecordingIndex()
    artifact = TfidfArtifact(
        output_dir=Path("."),
        vectorizer=None,
        svd=None,
        embeddings=np.array([[1.0, 0.0], [0.0, 1.0], [0.5, 0.5]], dtype=np.float32),
        index=index,
        tmdb_id_to_idx={1: 0, 2: 1, 3: 2},
        idx_to_tmdb_id={0: 1, 1: 2, 2: 3},
        manifest={"per_seed_candidates": 2},
    )

    assert artifact.recommend([1, 2], top_k=1) == [3]
    assert index.query_shapes == [(2, 2)]


def test_tfidf_seed_cache_preserves_known_and_unknown_seed_recommendations(
    tmp_path: Path,
):
    catalog_path = tmp_path / "catalog.parquet"
    pd.DataFrame(
        [
            {"tmdb_id": 1, "title": "space war", "overview": "space battle"},
            {"tmdb_id": 2, "title": "space rescue", "overview": "space mission"},
            {"tmdb_id": 3, "title": "family drama", "overview": "family dinner"},
        ]
    ).to_parquet(catalog_path, index=False)
    artifact = train_tfidf(
        catalog_path,
        tmp_path / "artifact",
        text_fields=("title", "overview"),
        min_df=1,
        max_features=None,
        embedding_dim=2,
        random_seed=42,
        dataset_version="fixture-v1",
        training_metadata={"per_seed_candidates": 2},
    )
    queries_path = tmp_path / "validation.parquet"
    pd.DataFrame({"seed_tmdb_ids": [[1, 3], [2]]}).to_parquet(queries_path, index=False)

    cached = build_tfidf_seed_cache(artifact, queries_path, query_limit=1, batch_size=1)

    assert set(cached.row_by_seed) == {1, 3}
    assert cached.recommend([1, 3], top_k=2) == artifact.recommend([1, 3], top_k=2)
    assert cached.recommend([2], top_k=2) == artifact.recommend([2], top_k=2)
