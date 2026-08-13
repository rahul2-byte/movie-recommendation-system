import pytest
from evaluation.metrics import (
    map_at_k,
    mrr_at_k,
    ndcg_at_k,
    ranking_metrics,
    sanitize_recommendations,
)


def test_sanitize_recommendations_excludes_seeds_duplicates_and_invalid_ids():
    assert sanitize_recommendations([0, 11, 12, 12, -1, 13], {11}, 3) == [12, 13]


def test_ranking_metrics_use_unique_relevant_items_at_k():
    metrics = ranking_metrics([2, 3, 4], {2, 4, 5}, k=2)

    assert metrics == {"recall": 1 / 3, "hit_rate": 1.0, "precision": 0.5}


def test_ranker_metrics_match_hand_computed_binary_relevance():
    labels = [1, 0, 1, 0]

    assert ndcg_at_k(labels, 3) == pytest.approx(0.9197207891)
    assert map_at_k(labels, 3) == pytest.approx(0.8333333333)
    assert mrr_at_k(labels, 3) == 1.0


@pytest.mark.parametrize("metric", [ndcg_at_k, map_at_k, mrr_at_k])
def test_ranker_metrics_reject_non_positive_k(metric):
    with pytest.raises(ValueError, match="k must be positive"):
        metric([1], 0)
