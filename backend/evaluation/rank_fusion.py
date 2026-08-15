"""Rank-based fusion and candidate contribution analysis for retrievers."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Protocol

import pyarrow.parquet as pq

from evaluation.metrics import sanitize_recommendations


class Recommender(Protocol):
    """Minimal interface required by evaluation-time recommenders."""

    def recommend(self, seed_tmdb_ids: list[int], top_k: int) -> list[int]:
        """Return up to ``top_k`` ranked candidate IDs."""
        ...


class RankFusionRecommender:
    """Reciprocal-rank fusion over independently ranked retriever outputs."""

    def __init__(
        self,
        recommenders: dict[str, Recommender],
        *,
        rank_constant: int,
        candidate_k: int,
    ) -> None:
        """Bind independent recommenders and validate fusion parameters."""
        if len(recommenders) < 2:
            raise ValueError("Rank fusion requires at least two recommenders")
        if rank_constant < 1 or candidate_k < 1:
            raise ValueError("rank_constant and candidate_k must be positive")
        self.recommenders = recommenders
        self.rank_constant = rank_constant
        self.candidate_k = candidate_k

    def recommend(self, seed_tmdb_ids: list[int], top_k: int) -> list[int]:
        """Return deterministic reciprocal-rank fusion results."""
        if top_k < 1:
            raise ValueError("top_k must be positive")
        seed_set = set(seed_tmdb_ids)
        scores: dict[int, float] = {}
        for recommender in self.recommenders.values():
            ranked = sanitize_recommendations(
                recommender.recommend(seed_tmdb_ids, self.candidate_k),
                seed_set,
                self.candidate_k,
            )
            for rank, item_id in enumerate(ranked, start=1):
                scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (
                    self.rank_constant + rank
                )
        return [
            item_id
            for item_id, _ in sorted(
                scores.items(), key=lambda item: (-item[1], item[0])
            )
        ][:top_k]


def analyze_candidate_overlap(
    als: Recommender,
    two_tower: Recommender,
    queries_path: Path,
    *,
    candidate_k: int,
    query_limit: int | None = None,
    progress_callback: Callable[[int, int], None] | None = None,
    first_name: str = "als",
    second_name: str = "two_tower",
) -> dict[str, float | int]:
    """Measure candidate overlap and held-out unique relevant contribution."""
    if candidate_k < 1:
        raise ValueError("candidate_k must be positive")
    source = pq.ParquetFile(queries_path)
    required = {"seed_tmdb_ids", "ground_truth_tmdb_ids"}
    missing = required - set(source.schema_arrow.names)
    if missing:
        raise ValueError(f"Query data is missing columns: {sorted(missing)}")
    total = (
        min(source.metadata.num_rows, query_limit)
        if query_limit
        else source.metadata.num_rows
    )
    count = 0
    jaccard_total = shared_total = als_unique_total = two_tower_unique_total = 0
    als_unique_relevant = two_tower_unique_relevant = 0
    any_shared = 0
    for batch in source.iter_batches(
        columns=["seed_tmdb_ids", "ground_truth_tmdb_ids"], batch_size=5_000
    ):
        for query in batch.to_pylist():
            if query_limit is not None and count == query_limit:
                break
            count += 1
            seeds = [int(value) for value in query["seed_tmdb_ids"]]
            relevant = {int(value) for value in query["ground_truth_tmdb_ids"]}
            als_candidates = set(als.recommend(seeds, candidate_k))
            two_tower_candidates = set(two_tower.recommend(seeds, candidate_k))
            shared = als_candidates & two_tower_candidates
            als_unique = als_candidates - two_tower_candidates
            two_tower_unique = two_tower_candidates - als_candidates
            union = als_candidates | two_tower_candidates
            jaccard_total += len(shared) / len(union) if union else 0.0
            shared_total += len(shared)
            als_unique_total += len(als_unique)
            two_tower_unique_total += len(two_tower_unique)
            als_unique_relevant += len(als_unique & relevant)
            two_tower_unique_relevant += len(two_tower_unique & relevant)
            any_shared += int(bool(shared))
        if progress_callback is not None:
            progress_callback(count, total)
        if query_limit is not None and count == query_limit:
            break
    if not count:
        raise ValueError(f"No queries evaluated from {queries_path}")
    return {
        "candidate_k": candidate_k,
        "query_count": count,
        "mean_jaccard": jaccard_total / count,
        "queries_with_shared_candidates_rate": any_shared / count,
        "mean_shared_candidates": shared_total / count,
        f"mean_{first_name}_unique_candidates": als_unique_total / count,
        f"mean_{second_name}_unique_candidates": two_tower_unique_total / count,
        f"{first_name}_unique_relevant_candidates": als_unique_relevant,
        f"{second_name}_unique_relevant_candidates": two_tower_unique_relevant,
    }
