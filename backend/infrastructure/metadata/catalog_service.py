"""TMDB-backed catalog queries used by the catalog API routes."""

from datetime import date

from infrastructure.clients.tmdb import get_tmdb_client
from infrastructure.metadata.movie_store import normalize_tmdb_summary


async def _fetch_movies(
    path: str, limit: int, params: dict[str, str] | None = None
) -> list[dict]:
    data = await get_tmdb_client().fetch_path(path, params)
    return [
        normalized
        for movie in data.get("results", [])[:limit]
        if isinstance(movie, dict)
        and movie.get("adult") is not True
        and (normalized := normalize_tmdb_summary(movie)) is not None
        and normalized.get("posterUrl")
    ]


async def fetch_trending_movies(
    limit: int = 20, page: int = 1, refresh_seed: int | None = None
) -> list[dict]:
    """Fetch and normalize the provider's weekly trending movie list."""
    params = {"page": str(page)}
    if refresh_seed is not None:
        params["page"] = str(max(1, (refresh_seed % 20) + page))
    return await _fetch_movies("/trending/movie/week", limit, params)


async def fetch_popular_movies(
    limit: int = 20, page: int = 1, refresh_seed: int | None = None
) -> list[dict]:
    """Fetch and normalize the provider's popular movie list."""
    params = {"page": str(page)}
    if refresh_seed is not None:
        params["page"] = str(max(1, (refresh_seed % 20) + page))
    return await _fetch_movies("/movie/popular", limit, params)


async def fetch_new_releases(
    limit: int = 20, page: int = 1, refresh_seed: int | None = None
) -> list[dict]:
    """Fetch and normalize recent releases for the catalog page."""
    return await _fetch_movies(
        "/discover/movie",
        limit,
        {
            "sort_by": "release_date.desc",
            "primary_release_date.lte": date.today().isoformat(),
            "page": str(
                max(1, (refresh_seed % 20) + page) if refresh_seed is not None else page
            ),
        },
    )


async def fetch_featured_movie() -> dict | None:
    """Return one display-ready weekly trending title for the homepage hero."""
    movies = await fetch_trending_movies(1)
    return movies[0] if movies else None


async def fetch_genres() -> list[dict]:
    """Return TMDB's movie genre catalog."""
    data = await get_tmdb_client().fetch_path("/genre/movie/list")
    return [
        genre
        for genre in data.get("genres", [])
        if isinstance(genre, dict)
        and isinstance(genre.get("id"), int)
        and isinstance(genre.get("name"), str)
    ]


async def fetch_similar_movies(
    tmdb_id: int,
    limit: int = 12,
    page: int = 1,
) -> list[dict]:
    """Return titles TMDB marks as similar to one canonical movie."""
    return await _fetch_movies(
        f"/movie/{tmdb_id}/similar",
        limit,
        {"page": str(page)},
    )


async def fetch_discover_movies(
    *,
    limit: int = 20,
    genre_id: int | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    rating_min: float | None = None,
    sort: str = "popularity",
    page: int = 1,
) -> list[dict]:
    """Discover movies with the small filter set exposed by the website."""
    sort_values = {
        "popularity": "popularity.desc",
        "rating": "vote_average.desc",
        "newest": "primary_release_date.desc",
    }
    params = {
        "page": str(page),
        "sort_by": sort_values[sort],
        "vote_count.gte": "100",
    }
    if genre_id is not None:
        params["with_genres"] = str(genre_id)
    if year_from is not None:
        params["primary_release_date.gte"] = f"{year_from}-01-01"
    if year_to is not None:
        params["primary_release_date.lte"] = f"{year_to}-12-31"
    if rating_min is not None:
        params["vote_average.gte"] = str(rating_min)
    return await _fetch_movies("/discover/movie", limit, params)
