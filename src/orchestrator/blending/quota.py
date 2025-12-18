from typing import List

from ..contracts import Candidate


def apply_quota(
    candidates: List[Candidate],
    quota: int,
) -> List[Candidate]:
    """
    Enforce per-retriever recall quota.

    Assumes candidates are already ordered
    by retriever-local relevance.
    """
    if quota <= 0:
        return []

    return candidates[:quota]
