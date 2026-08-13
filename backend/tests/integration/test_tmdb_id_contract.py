import pytest
from api.schemas.recommend import RecommendRequest
from common.types import Candidate, Query
from pydantic import ValidationError


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
