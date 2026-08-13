import asyncio

from application.contracts import RecommendationQuery
from serving.pipeline import BundleRecommendationPipeline


class _Recommender:
    def recommend(self, seed_tmdb_ids, seed_metadata, *, top_n):
        assert seed_tmdb_ids == [1]
        assert 1 in seed_metadata
        return [(20, 0.9), (30, 0.8)][:top_n]


class _MovieStore:
    async def get_many_by_tmdb_ids(self, tmdb_ids):
        movies = {
            1: {"tmdbId": 1, "title": "Seed"},
            20: {"tmdbId": 20, "title": "First"},
            30: {"tmdbId": 30, "title": "Second"},
        }
        return [movies[item_id] for item_id in tmdb_ids if item_id in movies]


def test_bundle_pipeline_returns_tmdb_metadata_in_ranked_order():
    pipeline = BundleRecommendationPipeline(_Recommender(), _MovieStore())

    results = asyncio.run(
        pipeline.recommend(RecommendationQuery(seed_tmdb_ids=[1]), top_n=2)
    )

    assert [item["tmdbId"] for item in results] == [20, 30]
    assert [item["score"] for item in results] == [0.9, 0.8]


def test_bundle_pipeline_excludes_seed_and_duplicate_candidates():
    class Recommender:
        def recommend(self, seed_tmdb_ids, seed_metadata, *, top_n):
            return [(1, 1.0), (20, 0.9), (20, 0.8), (30, 0.7)]

    pipeline = BundleRecommendationPipeline(Recommender(), _MovieStore())

    results = asyncio.run(
        pipeline.recommend(RecommendationQuery(seed_tmdb_ids=[1]), top_n=2)
    )

    assert [item["tmdbId"] for item in results] == [20, 30]
