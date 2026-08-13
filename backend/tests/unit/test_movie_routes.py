import asyncio

import api.v1.movies as movies
import pytest
from fastapi import HTTPException


class _Store:
    async def get_by_tmdb_id(self, tmdb_id: int):
        return {"tmdbId": tmdb_id, "title": "Example"}


class _MissingStore:
    async def get_by_tmdb_id(self, tmdb_id: int):
        return None


def test_tmdb_route_uses_movie_store_contract(monkeypatch):
    monkeypatch.setattr(movies, "get_movie_store", lambda: _Store())

    result = asyncio.run(movies.get_movie_by_tmdb_id(None, 603))

    assert result == {"tmdbId": 603, "title": "Example"}


def test_tmdb_route_returns_404_for_missing_movie(monkeypatch):
    monkeypatch.setattr(movies, "get_movie_store", lambda: _MissingStore())

    with pytest.raises(HTTPException) as error:
        asyncio.run(movies.get_movie_by_tmdb_id(None, 999999))

    assert error.value.status_code == 404
    assert error.value.detail == "Movie not found"
