"""Pure, testable recommendation metrics."""

from __future__ import annotations

from collections.abc import Iterable
from math import log2


def sanitize_recommendations(
    recommendations: Iterable[int], seed_ids: set[int], limit: int
) -> list[int]:
    """Keep the first valid, non-seed occurrence of each recommendation ID."""
    result: list[int] = []
    seen: set[int] = set()
    for item_id in recommendations:
        item_id = int(item_id)
        if item_id <= 0 or item_id in seed_ids or item_id in seen:
            continue
        result.append(item_id)
        seen.add(item_id)
        if len(result) == limit:
            break
    return result


def ranking_metrics(
    recommendations: Iterable[int], relevant_ids: set[int], k: int
) -> dict[str, float]:
    """Compute unweighted per-query retrieval metrics at K."""
    if k < 1:
        raise ValueError("k must be positive")
    relevant = {int(item_id) for item_id in relevant_ids if int(item_id) > 0}
    if not relevant:
        raise ValueError("relevant_ids must contain at least one valid ID")
    predicted = list(recommendations)[:k]
    hits = len(set(predicted) & relevant)
    return {
        "recall": hits / len(relevant),
        "hit_rate": float(hits > 0),
        "precision": hits / k,
    }


def _validated_labels(labels: Iterable[int], k: int) -> list[int]:
    if k < 1:
        raise ValueError("k must be positive")
    return [int(label) > 0 for label in list(labels)[:k]]


def ndcg_at_k(labels: Iterable[int], k: int) -> float:
    """Compute binary normalized discounted cumulative gain for ranked labels."""
    ranked = _validated_labels(labels, k)
    positives = sum(ranked)
    if not positives:
        return 0.0
    dcg = sum(label / log2(position + 2) for position, label in enumerate(ranked))
    ideal_dcg = sum(1.0 / log2(position + 2) for position in range(positives))
    return dcg / ideal_dcg


def map_at_k(labels: Iterable[int], k: int) -> float:
    """Compute binary mean average precision for one ranked query at K."""
    ranked = _validated_labels(labels, k)
    positives = sum(ranked)
    if not positives:
        return 0.0
    hits = 0
    precision_sum = 0.0
    for position, label in enumerate(ranked, start=1):
        if label:
            hits += 1
            precision_sum += hits / position
    return precision_sum / positives


def mrr_at_k(labels: Iterable[int], k: int) -> float:
    """Compute reciprocal rank of the first positive ranked item at K."""
    for position, label in enumerate(_validated_labels(labels, k), start=1):
        if label:
            return 1.0 / position
    return 0.0
