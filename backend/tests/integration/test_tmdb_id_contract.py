import asyncio

import numpy as np
import pytest
from api.schemas.recommend import RecommendRequest
from common.types import Candidate, Query
from pipeline.pipeline import RecommendationPipeline
from pydantic import ValidationError
from retrieval.models.tfidf import TfidfRetriever
from retrieval.models.two_tower import TwoTowerRetriever


def test_query_and_candidate_use_tmdb_ids():
    query = Query(seed_tmdb_ids=[603, 238])
    candidate = Candidate(tmdb_id=680)

    assert query.seed_tmdb_ids == [603, 238]
    assert candidate.item_id == 680


def test_recommend_request_requires_tmdb_seed_ids():
    request = RecommendRequest(seed_tmdb_ids=[603])

    assert request.seed_tmdb_ids == [603]
    with pytest.raises(ValidationError):
        RecommendRequest(seed_movie_ids=[603])


def test_recommend_request_rejects_invalid_seed_ids_and_limits():
    with pytest.raises(ValidationError):
        RecommendRequest(seed_tmdb_ids=[0])
    with pytest.raises(ValidationError):
        RecommendRequest(seed_tmdb_ids=[-1])
    with pytest.raises(ValidationError):
        RecommendRequest(seed_tmdb_ids=[603], limit=0)


def test_retriever_returns_tmdb_ids_and_excludes_tmdb_seeds():
    retriever = TfidfRetriever.__new__(TfidfRetriever)
    retriever.name = "tfidf"
    retriever.item_embeddings = np.array([[1.0, 0.0], [0.9, 0.1]], dtype=np.float32)
    retriever.tmdb_id_to_idx = {603: 0, 680: 1}
    retriever.idx_to_tmdb_id = {0: 603, 1: 680}

    class Index:
        ntotal = 2

        @staticmethod
        def search(vector, count):
            return np.array([[1.0, 0.9]], dtype=np.float32), np.array([[0, 1]])

    retriever.index = Index()

    result = asyncio.run(retriever.retrieve(Query(seed_tmdb_ids=[603]), top_k=2))

    assert result[0][0] == 680
    assert result[0][1] == pytest.approx(0.9)
    assert result[0][2] == "tfidf"


def test_two_tower_retrieves_each_seed_without_averaging_them():
    retriever = TwoTowerRetriever.__new__(TwoTowerRetriever)
    retriever.name = "two_tower"
    retriever.item_embeddings = np.array(
        [[1.0, 0.0], [0.0, 1.0], [0.8, 0.2]], dtype=np.float32
    )
    retriever.tmdb_id_to_idx = {10: 0, 20: 1, 30: 2}
    retriever.idx_to_tmdb_id = {0: 10, 1: 20, 2: 30}

    class Index:
        ntotal = 3
        calls = 0

        def search(self, vector, count):
            self.calls += 1
            position = int(np.argmax(vector[0]))
            return (
                np.array([[1.0, 0.8]], dtype=np.float32),
                np.array([[position, 2]], dtype=np.int64),
            )

    retriever.index = Index()
    result = asyncio.run(retriever.retrieve(Query(seed_tmdb_ids=[10, 20]), top_k=2))

    assert retriever.index.calls == 2
    assert [candidate[0] for candidate in result] == [30]


def test_pipeline_uses_tmdb_ids_for_metadata_lookup_and_response():
    class MovieStore:
        async def get_many_by_tmdb_ids(self, tmdb_ids):
            return [
                {
                    "tmdbId": tmdb_id,
                    "title": f"Movie {tmdb_id}",
                    "year": 2024,
                    "genres": ["Drama"],
                    "rating": 7.0,
                    "posterUrl": None,
                }
                for tmdb_id in tmdb_ids
            ]

    class RecallService:
        async def recall(self, query, top_k, request_id):
            assert query.seed_tmdb_ids == [603]
            return [Candidate(tmdb_id=680)]

    class FeatureBuilder:
        def build_features(self, seeds, candidates):
            assert [movie["tmdbId"] for movie in seeds] == [603]
            assert [movie["tmdbId"] for movie in candidates] == [680]
            return object()

    class Ranker:
        def rank(self, candidates, features_df, limit):
            return candidates

    pipeline = RecommendationPipeline(
        recall_service=RecallService(),
        feature_builder=FeatureBuilder(),
        ranker=Ranker(),
        movie_store=MovieStore(),
    )

    results = asyncio.run(
        pipeline.recommend(Query(seed_tmdb_ids=[603]), top_n=1, request_id="test")
    )

    assert results == [
        {
            "tmdbId": 680,
            "title": "Movie 680",
            "year": 2024,
            "genres": ["Drama"],
            "rating": 7.0,
            "posterUrl": None,
            "score": 0.0,
            "retrieval_sources": [],
        }
    ]
