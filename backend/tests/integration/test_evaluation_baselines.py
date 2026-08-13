from pathlib import Path

import pandas as pd
from evaluation.baselines import PopularityRecommender


def test_popularity_baseline_uses_training_counts_and_excludes_seeds(tmp_path: Path):
    train_path = tmp_path / "train.parquet"
    pd.DataFrame(
        {
            "user_id": [1, 2, 3, 4, 5, 6],
            "tmdb_id": [10, 20, 20, 30, 30, 30],
            "movielens_id": [1, 2, 2, 3, 3, 3],
            "rating": [3.0] * 6,
            "timestamp": list(range(6)),
        }
    ).to_parquet(train_path, index=False)

    recommender = PopularityRecommender.fit(train_path)

    assert recommender.recommend([30], top_k=3) == [20, 10]
