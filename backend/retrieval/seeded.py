"""Seed-wise candidate collection shared by offline retrievers."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class SeedCandidate:
    """One retriever result linked to its originating seed and rank."""
    seed_tmdb_id: int
    candidate_tmdb_id: int
    source: str
    score: float
    rank: int


def collect_seed_candidates(
    seed_tmdb_ids: Iterable[int],
    *,
    retrieve_one: Callable[[int, int], Iterable[tuple[int, float]]],
    source: str,
    top_k: int,
) -> list[SeedCandidate]:
    """Retrieve independently per seed without creating a pooled seed vector."""
    if top_k < 1:
        raise ValueError("top_k must be positive")
    seeds = list(
        dict.fromkeys(int(seed_id) for seed_id in seed_tmdb_ids if int(seed_id) > 0)
    )
    seed_set = set(seeds)
    candidate_records: list[SeedCandidate] = []
    for seed_id in seeds:
        # Each seed is queried independently because the retrievers expose
        # item-to-item indexes; pooling seeds before retrieval would require a
        # new user-vector contract and change the model semantics.
        seen: set[int] = set()
        rank = 0
        for candidate_id, score in retrieve_one(seed_id, top_k):
            candidate_id = int(candidate_id)
            if candidate_id <= 0 or candidate_id in seed_set or candidate_id in seen:
                continue
            seen.add(candidate_id)
            rank += 1
            candidate_records.append(
                SeedCandidate(seed_id, candidate_id, source, float(score), rank)
            )
            if rank == top_k:
                break
    return candidate_records


def order_candidate_ids(evidence: Iterable[SeedCandidate]) -> list[int]:
    """Order a single retriever's union by seed support, then best rank."""
    by_candidate: dict[int, list[SeedCandidate]] = defaultdict(list)
    for row in evidence:
        by_candidate[row.candidate_tmdb_id].append(row)
    return [
        candidate_id
        for candidate_id, rows in sorted(
            by_candidate.items(),
            key=lambda item: (
                -len({row.seed_tmdb_id for row in item[1]}),
                min(row.rank for row in item[1]),
                item[0],
            ),
        )
    ]
