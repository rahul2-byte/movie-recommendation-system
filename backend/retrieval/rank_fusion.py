"""Shared reciprocal-rank fusion primitives for training and serving."""

from collections.abc import Iterable, Mapping


def reciprocal_rank_score(ranks: Iterable[int], rank_constant: int) -> float:
    """Return reciprocal-rank fusion evidence for positive source ranks."""
    if rank_constant < 1:
        raise ValueError("rank_constant must be positive")
    return sum(1.0 / (rank_constant + rank) for rank in ranks if rank > 0)


def score_candidate_ranks(
    ranks_by_source: Mapping[str, Mapping[int, int]], rank_constant: int
) -> dict[int, float]:
    """Score every candidate from per-source one-based ranks deterministically."""
    candidate_ids = sorted(
        {candidate_id for source in ranks_by_source.values() for candidate_id in source}
    )
    return {
        candidate_id: reciprocal_rank_score(
            (source.get(candidate_id, 0) for source in ranks_by_source.values()),
            rank_constant,
        )
        for candidate_id in candidate_ids
    }
