from pathlib import Path

import pandas as pd
from evaluation.runner import evaluate_recommender, write_evaluation_artifacts


class _StubRecommender:
    def recommend(self, seed_tmdb_ids: list[int], top_k: int) -> list[int]:
        return [seed_tmdb_ids[0], 0, 2, 2, 3]


def test_runner_aggregates_metrics_and_writes_machine_readable_artifacts(
    tmp_path: Path,
):
    queries_path = tmp_path / "validation.parquet"
    pd.DataFrame(
        {
            "query_id": ["validation:1", "validation:2"],
            "seed_tmdb_ids": [[1], [1]],
            "ground_truth_tmdb_ids": [[2, 4], [5]],
            "history_end_timestamp": [1, 2],
            "ground_truth_start_timestamp": [2, 3],
        }
    ).to_parquet(queries_path, index=False)

    progress: list[tuple[int, int]] = []
    summary = evaluate_recommender(
        _StubRecommender(),
        queries_path,
        catalog_size=10,
        k_values=(1, 2),
        progress_callback=lambda completed, total: progress.append((completed, total)),
    )
    output_dir = tmp_path / "artifacts"
    write_evaluation_artifacts(output_dir, {"partition": "validation"}, summary)

    assert summary["query_count"] == 2
    assert summary["failures"] == 0
    assert summary["metrics"]["2"]["recall_at_k"] == 0.25
    assert summary["metrics"]["2"]["hit_rate_at_k"] == 0.5
    assert summary["metrics"]["2"]["catalog_coverage_at_k"] == 0.2
    assert progress[-1] == (2, 2)
    assert (output_dir / "config.json").is_file()
    assert (output_dir / "summary.json").is_file()


def test_runner_reports_final_progress_for_a_query_limit_inside_one_batch(
    tmp_path: Path,
):
    queries_path = tmp_path / "validation.parquet"
    pd.DataFrame(
        {
            "query_id": ["validation:1", "validation:2"],
            "seed_tmdb_ids": [[1], [1]],
            "ground_truth_tmdb_ids": [[2], [3]],
        }
    ).to_parquet(queries_path, index=False)

    progress: list[tuple[int, int]] = []
    evaluate_recommender(
        _StubRecommender(),
        queries_path,
        catalog_size=10,
        k_values=(1,),
        query_limit=1,
        progress_callback=lambda completed, total: progress.append((completed, total)),
    )

    assert progress[-1] == (1, 1)
