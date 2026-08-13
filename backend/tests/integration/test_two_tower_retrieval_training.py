from pathlib import Path

import pandas as pd
from training.retrieval.build_content_retriever import build_exact_seed_cache
from training.retrieval.build_two_tower import train_two_tower


def test_train_two_tower_writes_loadable_tmdb_keyed_artifact(tmp_path: Path):
    train_path = tmp_path / "train.parquet"
    pd.DataFrame(
        {
            "user_id": [1, 1, 1, 2, 2, 2, 3, 3, 3],
            "tmdb_id": [10, 20, 30, 10, 30, 20, 20, 10, 30],
            "rating": [5.0] * 9,
            "timestamp": list(range(1, 10)),
        }
    ).to_parquet(train_path, index=False)

    progress: list[tuple[int, str]] = []
    artifact = train_two_tower(
        train_path,
        tmp_path / "artifact",
        embedding_dim=4,
        batch_size=2,
        epochs=1,
        learning_rate=0.01,
        max_pairs_per_user=2,
        random_seed=42,
        dataset_version="fixture-v1",
        per_seed_candidates=2,
        progress_callback=lambda completed, stage: progress.append((completed, stage)),
    )

    assert artifact.manifest["model_type"] == "two_tower"
    assert artifact.manifest["pair_strategy"] == "adjacent_bidirectional"
    assert 10 not in artifact.recommend([10], top_k=2)
    assert artifact.recommend([999], top_k=2) == []
    assert progress[-1] == (6, "verify artifact")

    queries_path = tmp_path / "validation.parquet"
    pd.DataFrame({"seed_tmdb_ids": [[10], [20]]}).to_parquet(queries_path, index=False)
    cached = build_exact_seed_cache(artifact, queries_path, batch_size=1)
    assert cached.recommend([10], top_k=2) == artifact.recommend([10], top_k=2)
