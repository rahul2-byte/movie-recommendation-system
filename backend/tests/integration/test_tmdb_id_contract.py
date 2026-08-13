import pytest
from api.schemas.recommend import MovieOut, RecommendRequest
from application.contracts import RecommendationQuery
from pydantic import ValidationError
from retrieval.contracts import RetrievalCandidate


def test_query_and_candidate_use_tmdb_ids():
    query = RecommendationQuery(seed_tmdb_ids=[603, 238])
    candidate = RetrievalCandidate(tmdb_id=680)

    assert query.seed_tmdb_ids == [603, 238]
    assert candidate.item_id == 680


def test_movie_response_schema_declares_tmdb_id_once():
    movie = MovieOut(
        tmdbId=680,
        title="Example",
        year=1999,
        genres=[],
        posterUrl=None,
        rating=None,
    )

    assert movie.tmdbId == 680
    assert list(MovieOut.model_fields).count("tmdbId") == 1


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
