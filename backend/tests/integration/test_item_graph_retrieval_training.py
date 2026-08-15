from pathlib import Path

import pandas as pd
from training.retrieval.item_graph_trainer import (
    build_item_graph_seed_cache,
    train_item_graph,
)


def test_item_graph_writes_tmdb_keyed_ranked_neighbors(tmp_path: Path):
    train_path = tmp_path / "train.parquet"
    pd.DataFrame(
        {
            "user_id": [1, 1, 2, 2, 3, 3],
            "tmdb_id": [10, 20, 10, 30, 20, 30],
            "rating": [5.0, 4.0, 5.0, 3.0, 4.0, 5.0],
        }
    ).to_parquet(train_path, index=False)

    progress: list[tuple[int, str]] = []
    artifact = train_item_graph(
        train_path,
        tmp_path / "artifact",
        neighbor_count=2,
        k1=1.2,
        b=0.75,
        num_threads=1,
        random_seed=42,
        dataset_version="fixture-v1",
        per_seed_candidates=2,
        parquet_batch_size=2,
        progress_callback=lambda completed, stage: progress.append((completed, stage)),
    )

    assert artifact.manifest["model_type"] == "item_graph"
    assert set(artifact.recommend([10], top_k=2)) == {20, 30}
    assert artifact.recommend([999], top_k=2) == []
    assert progress[-1] == (6, "verify artifact")

    queries_path = tmp_path / "validation.parquet"
    pd.DataFrame({"seed_tmdb_ids": [[10], [20]]}).to_parquet(queries_path, index=False)
    cached = build_item_graph_seed_cache(artifact, queries_path, batch_size=1)
    assert cached.recommend([10], top_k=2) == artifact.recommend([10], top_k=2)
