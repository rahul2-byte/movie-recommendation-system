"""TMDB-backed catalog queries used by the catalog API routes."""

from infrastructure.clients.tmdb import get_tmdb_client

IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"


def normalize_tmdb_movie(movie: dict) -> dict:
    """Convert a TMDB payload into the frontend catalog response shape."""
    return {
        "tmdbId": movie["id"],
        "title": movie["title"],
        "year": int(movie["release_date"][:4]) if movie.get("release_date") else None,
        "genres": [],
        "rating": movie.get("vote_average"),
        "posterUrl": (
            f"{IMAGE_BASE_URL}{movie['poster_path']}"
            if movie.get("poster_path")
            else None
        ),
        "overview": movie.get("overview"),
    }


async def _fetch_movies(
    path: str, limit: int, params: dict[str, str] | None = None
) -> list[dict]:
    data = await get_tmdb_client().fetch_path(path, params)
    return [normalize_tmdb_movie(m) for m in data["results"][:limit]]


async def fetch_trending_movies(limit: int = 20) -> list[dict]:
    """Fetch and normalize the provider's weekly trending movie list."""
    return await _fetch_movies("/trending/movie/week", limit)


async def fetch_popular_movies(limit: int = 20) -> list[dict]:
    """Fetch and normalize the provider's popular movie list."""
    return await _fetch_movies("/movie/popular", limit)


async def fetch_new_releases(limit: int = 20) -> list[dict]:
    """Fetch and normalize recent releases for the catalog page."""
    return await _fetch_movies(
        "/discover/movie",
        limit,
        {
            "sort_by": "release_date.desc",
            "primary_release_date.lte": "2025-12-31",
        },
    )
