from pathlib import Path

import pandas as pd
from evaluation.rank_fusion import RankFusionRecommender, analyze_candidate_overlap


class StaticRecommender:
    def __init__(self, recommendations: list[int]) -> None:
        self.recommendations = recommendations

    def recommend(self, seed_tmdb_ids: list[int], top_k: int) -> list[int]:
        return self.recommendations[:top_k]


def test_rrf_combines_ranked_candidates_without_using_raw_scores():
    fusion = RankFusionRecommender(
        {
            "als": StaticRecommender([10, 20, 30]),
            "two_tower": StaticRecommender([20, 40, 10]),
        },
        rank_constant=60,
        candidate_k=3,
    )

    assert fusion.recommend([1], top_k=4) == [20, 10, 40, 30]


def test_overlap_reports_unique_relevant_candidates(tmp_path: Path):
    queries_path = tmp_path / "validation.parquet"
    pd.DataFrame(
        {
            "seed_tmdb_ids": [[1]],
            "ground_truth_tmdb_ids": [[20, 40]],
        }
    ).to_parquet(queries_path, index=False)

    summary = analyze_candidate_overlap(
        StaticRecommender([10, 20]),
        StaticRecommender([20, 40]),
        queries_path,
        candidate_k=2,
    )

    assert summary["mean_jaccard"] == 1 / 3
    assert summary["als_unique_relevant_candidates"] == 0
    assert summary["two_tower_unique_relevant_candidates"] == 1


def test_overlap_uses_the_retriever_names_in_evidence_keys(tmp_path: Path):
    queries_path = tmp_path / "validation.parquet"
    pd.DataFrame({"seed_tmdb_ids": [[1]], "ground_truth_tmdb_ids": [[20]]}).to_parquet(
        queries_path, index=False
    )

    summary = analyze_candidate_overlap(
        StaticRecommender([10]),
        StaticRecommender([20]),
        queries_path,
        candidate_k=1,
        first_name="als",
        second_name="item_graph",
    )

    assert summary["item_graph_unique_relevant_candidates"] == 1
