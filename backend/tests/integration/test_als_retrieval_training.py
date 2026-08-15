from pathlib import Path

import pandas as pd
from training.retrieval.als_trainer import train_als
from training.retrieval.content_retriever import build_exact_seed_cache


def test_train_als_writes_loadable_tmdb_keyed_artifact(tmp_path: Path):
    train_path = tmp_path / "train.parquet"
    pd.DataFrame(
        {
            "user_id": [1, 1, 2, 2, 3, 3],
            "tmdb_id": [10, 20, 10, 30, 20, 30],
            "rating": [5.0, 4.0, 5.0, 3.0, 4.0, 5.0],
        }
    ).to_parquet(train_path, index=False)

    progress: list[tuple[int, str]] = []
    artifact = train_als(
        train_path,
        tmp_path / "artifact",
        factors=2,
        regularization=0.1,
        alpha=10.0,
        iterations=1,
        num_threads=1,
        random_seed=42,
        dataset_version="fixture-v1",
        per_seed_candidates=2,
        parquet_batch_size=2,
        progress_callback=lambda completed, stage: progress.append((completed, stage)),
    )

    assert artifact.manifest["id_schema_version"] == "tmdb-keyed-v1"
    assert artifact.idx_to_tmdb_id == {0: 10, 1: 20, 2: 30}
    assert 10 not in artifact.recommend([10], top_k=2)
    assert artifact.recommend([999], top_k=2) == []
    assert (tmp_path / "artifact" / "faiss.index").is_file()
    assert progress[-1] == (5, "verify artifact")

    queries_path = tmp_path / "validation.parquet"
    pd.DataFrame({"seed_tmdb_ids": [[10], [20]]}).to_parquet(queries_path, index=False)
    cached = build_exact_seed_cache(artifact, queries_path, batch_size=1)
    assert cached.recommend([10], top_k=2) == artifact.recommend([10], top_k=2)
