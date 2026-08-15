"""Pure candidate collection and reciprocal-rank fusion for serving."""

from __future__ import annotations

from typing import Any

from retrieval.rank_fusion import score_candidate_ranks


def collect_source_candidates(
    retriever: Any, seed_tmdb_ids: list[int], top_k: int
) -> dict[int, int]:
    """Collect one retriever's candidates using seed support and best rank."""
    ranks_by_candidate_id: dict[int, list[int]] = {}
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
            ranks_by_candidate_id.setdefault(candidate_id, []).append(rank)
            if rank == top_k:
                break
    candidate_ids_by_support = sorted(
        ranks_by_candidate_id,
        key=lambda movie_id: (
            -len(ranks_by_candidate_id[movie_id]),
            min(ranks_by_candidate_id[movie_id]),
            movie_id,
        ),
    )[:top_k]
    return {
        movie_id: rank
        for rank, movie_id in enumerate(candidate_ids_by_support, start=1)
    }


def fuse_reciprocal_ranks(
    ranks_by_retriever: dict[str, dict[int, int]],
    rank_constant: int,
    candidate_limit: int,
) -> list[tuple[int, float]]:
    """Fuse source ranks without assuming comparable raw model scores."""
    # ALS, graph, content, and neural scores have different numerical scales.
    # Rank fusion keeps one source from dominating merely because its raw
    # similarity values are larger.
    rrf_scores_by_candidate_id = score_candidate_ranks(
        ranks_by_retriever, rank_constant
    )
    return sorted(
        (
            (movie_id, rrf_scores_by_candidate_id[movie_id])
            for movie_id in rrf_scores_by_candidate_id
        ),
        key=lambda item: (-item[1], item[0]),
    )[:candidate_limit]
