import pytest
from serving.benchmark import summarize_latencies, validate_seed_metadata


def test_latency_summary_reports_percentiles_and_rejects_empty_samples():
    assert summarize_latencies([1.0, 2.0, 3.0]) == {
        "count": 3,
        "mean": 2.0,
        "p50": 2.0,
        "p95": pytest.approx(2.9),
        "p99": pytest.approx(2.98),
    }

    with pytest.raises(ValueError, match="empty"):
        summarize_latencies([])


def test_benchmark_rejects_incomplete_seed_metadata():
    with pytest.raises(ValueError, match="missing TMDB metadata"):
        validate_seed_metadata([603, 238], {603: {"tmdbId": 603}})
