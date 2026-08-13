"""TMDB-backed movie metadata for the operational TMDB-ID contract."""

from __future__ import annotations

import asyncio
from typing import Any, Protocol

from common.clients.tmdb import get_tmdb_client
from common.logger import get_logger
from configs.settings import TMDB_IMAGE_BASE, TMDB_POSTER_SIZE

log = get_logger(__name__)


class TMDBMovieClient(Protocol):
    async def fetch_movie_full(self, tmdb_id: int) -> dict[str, Any]: ...

    async def fetch_path(
        self, path: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]: ...


def _image_url(path: object, size: str) -> str | None:
    return f"{TMDB_IMAGE_BASE}/{size}{path}" if isinstance(path, str) and path else None


def _normalize_movie(movie: dict[str, Any]) -> dict[str, Any] | None:
    tmdb_id = movie.get("id")
    if not isinstance(tmdb_id, int) or tmdb_id <= 0:
        return None
    credits = movie.get("credits") if isinstance(movie.get("credits"), dict) else {}
    keywords = movie.get("keywords") if isinstance(movie.get("keywords"), dict) else {}
    release_date = movie.get("release_date")
    year = (
        int(release_date[:4])
        if isinstance(release_date, str) and len(release_date) >= 4
        else None
    )
    return {
        "movieId": tmdb_id,
        "tmdbId": tmdb_id,
        "title": movie.get("title") or movie.get("original_title"),
        "year": year,
        "genres": [
            genre["name"]
            for genre in movie.get("genres", [])
            if isinstance(genre, dict) and isinstance(genre.get("name"), str)
        ],
        "keywords": [
            keyword["name"]
            for keyword in keywords.get("keywords", [])
            if isinstance(keyword, dict) and isinstance(keyword.get("name"), str)
        ],
        "top_cast": [
            member["name"]
            for member in credits.get("cast", [])[:5]
            if isinstance(member, dict) and isinstance(member.get("name"), str)
        ],
        "director": next(
            (
                member["name"]
                for member in credits.get("crew", [])
                if isinstance(member, dict)
                and member.get("job") == "Director"
                and isinstance(member.get("name"), str)
            ),
            None,
        ),
        "posterUrl": _image_url(movie.get("poster_path"), TMDB_POSTER_SIZE),
        "backdropUrl": _image_url(movie.get("backdrop_path"), "original"),
        "overview": movie.get("overview"),
        "tagline": movie.get("tagline"),
        "releaseDate": release_date,
        "runtime": movie.get("runtime"),
        "runtime_minutes": movie.get("runtime"),
        "rating": movie.get("vote_average"),
        "voteAverage": movie.get("vote_average"),
        "voteCountTmdb": movie.get("vote_count"),
        "popularity": movie.get("popularity"),
        "language": movie.get("original_language"),
        "country": next(
            (
                country["name"]
                for country in movie.get("production_countries", [])
                if isinstance(country, dict) and isinstance(country.get("name"), str)
            ),
            None,
        ),
        "collection_name": (
            movie["belongs_to_collection"].get("name")
            if isinstance(movie.get("belongs_to_collection"), dict)
            else None
        ),
    }


class MovieStore:
    """Fetch operational movie metadata from TMDB without a local replica."""

    def __init__(self, tmdb_client: TMDBMovieClient | None = None):
        self.tmdb_client = tmdb_client or get_tmdb_client()

    async def get(self, tmdb_id: int) -> dict[str, Any] | None:
        return _normalize_movie(await self.tmdb_client.fetch_movie_full(int(tmdb_id)))

    async def get_by_tmdb_id(self, tmdb_id: int) -> dict[str, Any] | None:
        return await self.get(tmdb_id)

    async def get_many(self, tmdb_ids: list[int]) -> list[dict[str, Any]]:
        """Fetch metadata while allowing individual optional lookups to fail.

        Recommendation retrieval can still produce useful candidates when one
        metadata request is unavailable, so failed records are omitted rather
        than aborting the entire batch.
        """
        responses = await asyncio.gather(
            *(self.get(tmdb_id) for tmdb_id in tmdb_ids), return_exceptions=True
        )
        movies: list[dict[str, Any]] = []
        for tmdb_id, response in zip(tmdb_ids, responses, strict=True):
            if isinstance(response, Exception):
                log.warning("Movie metadata lookup failed", tmdb_id=tmdb_id)
                continue
            if response is not None:
                movies.append(response)
        return movies

    async def get_many_by_tmdb_ids(self, tmdb_ids: list[int]) -> list[dict[str, Any]]:
        return await self.get_many(tmdb_ids)

    async def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        data = await self.tmdb_client.fetch_path("/search/movie", {"query": query})
        return [
            {
                "tmdbId": movie["id"],
                "movieId": movie["id"],
                "title": movie.get("title"),
            }
            for movie in data.get("results", [])[:limit]
            if isinstance(movie, dict)
            and isinstance(movie.get("id"), int)
            and movie["id"] > 0
        ]
