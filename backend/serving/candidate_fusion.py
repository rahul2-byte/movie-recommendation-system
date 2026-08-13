"""Pure candidate collection and reciprocal-rank fusion for serving."""

from __future__ import annotations

from typing import Any


def collect_source_candidates(
    retriever: Any, seed_tmdb_ids: list[int], top_k: int
) -> dict[int, int]:
    """Collect one retriever's candidates using seed support and best rank."""
    evidence: dict[int, list[int]] = {}
    seed_set = set(seed_tmdb_ids)
    for seed_tmdb_id in seed_tmdb_ids:
        seen: set[int] = set()
        rank = 0
        for candidate_id, _ in retriever.retrieve_one(seed_tmdb_id, top_k):
            candidate_id = int(candidate_id)
            # Seeds are already known user preferences and must not consume a
            # recommendation slot. Duplicate results from one seed add no new
            # evidence, so only the first occurrence contributes a rank.
            if candidate_id <= 0 or candidate_id in seed_set or candidate_id in seen:
                continue
            seen.add(candidate_id)
            rank += 1
            evidence.setdefault(candidate_id, []).append(rank)
            if rank == top_k:
                break
    ordered = sorted(
        evidence,
        key=lambda movie_id: (
            -len(evidence[movie_id]),
            min(evidence[movie_id]),
            movie_id,
        ),
    )[:top_k]
    return {movie_id: rank for rank, movie_id in enumerate(ordered, start=1)}


def fuse_reciprocal_ranks(
    source_ranks: dict[str, dict[int, int]],
    rank_constant: int,
    candidate_limit: int,
) -> list[tuple[int, float]]:
    """Fuse source ranks without assuming comparable raw model scores."""
    # ALS, graph, content, and neural scores have different numerical scales.
    # Rank fusion keeps one source from dominating merely because its raw
    # similarity values are larger.
    candidate_ids = sorted(
        {movie_id for rows in source_ranks.values() for movie_id in rows}
    )
    scores = {
        movie_id: sum(
            1.0 / (rank_constant + rank)
            for rows in source_ranks.values()
            if (rank := rows.get(movie_id))
        )
        for movie_id in candidate_ids
    }
    return sorted(
        ((movie_id, scores[movie_id]) for movie_id in candidate_ids),
        key=lambda item: (-item[1], item[0]),
    )[:candidate_limit]
