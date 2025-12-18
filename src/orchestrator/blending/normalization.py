import numpy as np
from typing import Iterable, List


def normalize_scores(scores: Iterable[float]) -> List[float]:
    """
    Rank-based normalization.

    Converts raw scores → [0, 1] range based on rank.
    Robust across retrievers with different score distributions.
    """
    scores = np.asarray(scores, dtype=np.float32)

    if scores.size == 0:
        return []

    ranks = scores.argsort().argsort()
    normalized = ranks / max(len(scores) - 1, 1)

    return normalized.tolist()
