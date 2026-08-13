"""Minimal, reproducible recommendation baselines."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pyarrow.parquet as pq

from evaluation.metrics import sanitize_recommendations


class PopularityRecommender:
    """Global item popularity calculated from training interactions only."""

    def __init__(self, ordered_tmdb_ids: list[int]):
        """Store the deterministic popularity ordering learned from training."""
        self._ordered_tmdb_ids = ordered_tmdb_ids

    @classmethod
    def fit(cls, train_path: Path) -> PopularityRecommender:
        """Fit global item popularity from training interactions only."""
        counts: Counter[int] = Counter()
        source = pq.ParquetFile(train_path)
        if "tmdb_id" not in source.schema_arrow.names:
            raise ValueError(f"Training data is missing tmdb_id: {train_path}")
        for batch in source.iter_batches(columns=["tmdb_id"], batch_size=250_000):
            counts.update(
                int(item_id) for item_id in batch.column(0).to_pylist() if item_id
            )
        return cls(
            [
                item_id
                for item_id, _ in sorted(
                    counts.items(), key=lambda pair: (-pair[1], pair[0])
                )
            ]
        )

    def recommend(self, seed_tmdb_ids: list[int], top_k: int) -> list[int]:
        """Return popular items while excluding selected seed movies."""
        if top_k < 1:
            raise ValueError("top_k must be positive")
        return sanitize_recommendations(
            self._ordered_tmdb_ids, set(seed_tmdb_ids), top_k
        )
