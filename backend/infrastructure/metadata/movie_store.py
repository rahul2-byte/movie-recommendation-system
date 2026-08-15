"""TMDB-backed movie metadata for the operational TMDB-ID contract."""

from __future__ import annotations

import asyncio
from typing import Any, Protocol

from configuration.settings import TMDB_IMAGE_BASE, TMDB_POSTER_SIZE
from observability.logging import get_logger

from infrastructure.clients.tmdb import get_tmdb_client

log = get_logger(__name__)


class TMDBMovieClient(Protocol):
    """Subset of the TMDB client needed by the metadata repository."""

    async def fetch_movie_full(self, tmdb_id: int) -> dict[str, Any]:
        """Fetch one full movie payload including enrichment fields."""
        ...

    async def fetch_path(
        self, path: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Fetch a provider endpoint used by catalog routes."""
        ...


def _image_url(path: object, size: str) -> str | None:
    """Build a TMDB image URL or return ``None`` for missing artwork."""
    return f"{TMDB_IMAGE_BASE}/{size}{path}" if isinstance(path, str) and path else None


def normalize_tmdb_movie(movie: dict[str, Any]) -> dict[str, Any] | None:
    """Map provider metadata to the canonical API movie representation."""
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
        """Initialize the repository with an injectable TMDB client."""
        self.tmdb_client = tmdb_client or get_tmdb_client()

    async def get(self, tmdb_id: int) -> dict[str, Any] | None:
        """Fetch one movie by its canonical TMDB identifier."""
        return normalize_tmdb_movie(
            await self.tmdb_client.fetch_movie_full(int(tmdb_id))
        )

    async def get_many(self, tmdb_ids: list[int]) -> list[dict[str, Any]]:
        """Fetch metadata while allowing individual optional lookups to fail.

        Recommendation retrieval can still produce useful candidates when one
        metadata request is unavailable, so failed records are omitted rather
        than aborting the entire batch.
        """
        metadata_results = await asyncio.gather(
            *(self.get(tmdb_id) for tmdb_id in tmdb_ids), return_exceptions=True
        )
        normalized_movies: list[dict[str, Any]] = []
        for tmdb_id, metadata_result in zip(tmdb_ids, metadata_results, strict=True):
            if isinstance(metadata_result, Exception):
                log.warning("Movie metadata lookup failed", tmdb_id=tmdb_id)
                continue
            if metadata_result is not None:
                normalized_movies.append(metadata_result)
        return normalized_movies

    async def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search the provider catalog for display-ready movie records."""
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
