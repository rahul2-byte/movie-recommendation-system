import pytest
import pandas as pd
from unittest.mock import MagicMock, AsyncMock
from fastapi.testclient import TestClient
from main import app
from common.services.movie_store import MovieStore
from common.types import Query, Candidate

@pytest.fixture
def mock_movies_df():
    return pd.DataFrame({
        "movieId": [1, 2, 3],
        "title": ["Toy Story (1995)", "Jumanji (1995)", "Grumpier Old Men (1995)"],
        "genres": ["Animation|Children|Comedy", "Adventure|Children|Fantasy", "Comedy|Romance"]
    })

@pytest.fixture
def mock_links_df():
    return pd.DataFrame({
        "movieId": [1, 2, 3],
        "tmdbId": [862, 8844, 15602]
    })

@pytest.fixture
def movie_store(mock_movies_df, mock_links_df):
    return MovieStore(mock_movies_df, mock_links_df)

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture
def mock_recall_service():
    service = MagicMock()
    service.recall = AsyncMock(return_value=[
        Candidate(movie_id=10, score=0.9, sources=["source1"]),
        Candidate(movie_id=20, score=0.8, sources=["source2"])
    ])
    return service

@pytest.fixture
def mock_ranker():
    ranker = MagicMock()
    # Mock rank method to return same candidates but with rank_score set
    def mock_rank(candidates, features_df, limit):
        for i, c in enumerate(candidates):
            c.rank_score = 1.0 - (i * 0.1)
        return candidates[:limit]
    ranker.rank = MagicMock(side_effect=mock_rank)
    return ranker
