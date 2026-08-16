"""TMDB-backed movie metadata for the operational TMDB-ID contract."""

from __future__ import annotations

import asyncio
from typing import Any, Protocol

from configuration.settings import TMDB_IMAGE_BASE, TMDB_POSTER_SIZE
from observability.logging import get_logger

from infrastructure.clients.tmdb import get_tmdb_client

log = get_logger(__name__)

TMDB_GENRES = {
    12: "Adventure",
    14: "Fantasy",
    16: "Animation",
    18: "Drama",
    27: "Horror",
    28: "Action",
    35: "Comedy",
    36: "History",
    37: "Western",
    53: "Thriller",
    80: "Crime",
    99: "Documentary",
    878: "Science Fiction",
    9648: "Mystery",
    10402: "Music",
    10749: "Romance",
    10751: "Family",
    10752: "War",
    10770: "TV Movie",
}


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


def _year(release_date: object) -> int | None:
    """Return the four-digit release year when provider data is valid."""
    if not isinstance(release_date, str) or len(release_date) < 4:
        return None
    try:
        return int(release_date[:4])
    except ValueError:
        return None


def normalize_tmdb_summary(movie: dict[str, Any]) -> dict[str, Any] | None:
    """Map a TMDB list item to the shared display-ready movie summary."""
    tmdb_id = movie.get("id")
    if not isinstance(tmdb_id, int) or tmdb_id <= 0:
        return None
    genres = movie.get("genres")
    genre_names = (
        [
            genre["name"]
            for genre in genres
            if isinstance(genre, dict) and isinstance(genre.get("name"), str)
        ]
        if isinstance(genres, list)
        else [
            TMDB_GENRES[genre_id]
            for genre_id in movie.get("genre_ids", [])
            if genre_id in TMDB_GENRES
        ]
    )
    return {
        "tmdbId": tmdb_id,
        "movieId": tmdb_id,
        "title": movie.get("title") or movie.get("original_title") or "Untitled",
        "year": _year(movie.get("release_date")),
        "genres": genre_names,
        "posterUrl": _image_url(movie.get("poster_path"), TMDB_POSTER_SIZE),
        "backdropUrl": _image_url(movie.get("backdrop_path"), "w1280"),
        "rating": movie.get("vote_average"),
        "overview": movie.get("overview"),
    }


def normalize_tmdb_movie(movie: dict[str, Any]) -> dict[str, Any] | None:
    """Map provider metadata to the canonical API movie representation."""
    tmdb_id = movie.get("id")
    if not isinstance(tmdb_id, int) or tmdb_id <= 0:
        return None
    credits = movie.get("credits") if isinstance(movie.get("credits"), dict) else {}
    keywords = movie.get("keywords") if isinstance(movie.get("keywords"), dict) else {}
    summary = normalize_tmdb_summary(movie)
    if summary is None:
        return None
    release_date = movie.get("release_date")
    videos = movie.get("videos") if isinstance(movie.get("videos"), dict) else {}
    trailers = [
        video
        for video in videos.get("results", [])
        if isinstance(video, dict)
        and video.get("site") == "YouTube"
        and video.get("type") == "Trailer"
        and isinstance(video.get("key"), str)
    ]
    trailer = next((video for video in trailers if video.get("official")), None)
    trailer = trailer or (trailers[0] if trailers else None)
    cast = [
        member["name"]
        for member in credits.get("cast", [])[:5]
        if isinstance(member, dict) and isinstance(member.get("name"), str)
    ]
    return {
        **summary,
        "keywords": [
            keyword["name"]
            for keyword in keywords.get("keywords", [])
            if isinstance(keyword, dict) and isinstance(keyword.get("name"), str)
        ],
        "cast": cast,
        "top_cast": cast,
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
        "trailerUrl": (
            f"https://www.youtube.com/watch?v={trailer['key']}" if trailer else None
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
            if metadata_result is not None and (
                "posterUrl" not in metadata_result or metadata_result.get("posterUrl")
            ):
                normalized_movies.append(metadata_result)
        return normalized_movies

    async def search(
        self,
        query: str,
        limit: int = 10,
        page: int = 1,
    ) -> list[dict[str, Any]]:
        """Search the provider catalog for display-ready movie records."""
        data = await self.tmdb_client.fetch_path(
            "/search/movie",
            {"query": query, "page": str(page)},
        )
        return [
            normalized
            for movie in data.get("results", [])[:limit]
            if isinstance(movie, dict)
            and movie.get("adult") is not True
            and (normalized := normalize_tmdb_summary(movie)) is not None
            and normalized.get("posterUrl")
        ]
