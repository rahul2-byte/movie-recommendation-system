"""HTTP endpoints for TMDB catalog discovery lists."""

from fastapi import APIRouter, Query
from infrastructure.metadata.catalog_service import (
    fetch_discover_movies,
    fetch_featured_movie,
    fetch_genres,
    fetch_new_releases,
    fetch_popular_movies,
    fetch_trending_movies,
)

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/trending")
async def trending(
    limit: int = Query(20, ge=5, le=50),
    page: int = Query(1, ge=1, le=500),
    refresh_seed: int | None = Query(None, ge=0),
):
    """Return currently trending movies from the metadata provider."""
    return await fetch_trending_movies(limit, page, refresh_seed)


@router.get("/popular")
async def popular(
    limit: int = Query(20, ge=5, le=50),
    page: int = Query(1, ge=1, le=500),
    refresh_seed: int | None = Query(None, ge=0),
):
    """Return popular movies from the metadata provider."""
    return await fetch_popular_movies(limit, page, refresh_seed)


@router.get("/new")
async def new_releases(
    limit: int = Query(20, ge=5, le=50),
    page: int = Query(1, ge=1, le=500),
    refresh_seed: int | None = Query(None, ge=0),
):
    """Return recent movie releases from the metadata provider."""
    return await fetch_new_releases(limit, page, refresh_seed)


@router.get("/featured")
async def featured():
    """Return the featured movie used by the homepage hero."""
    return await fetch_featured_movie()


@router.get("/genres")
async def genres():
    """Return the provider's supported movie genres."""
    return await fetch_genres()


@router.get("/discover")
async def discover(
    limit: int = Query(20, ge=5, le=50),
    genre_id: int | None = Query(None, gt=0),
    year_from: int | None = Query(None, ge=1900, le=2100),
    year_to: int | None = Query(None, ge=1900, le=2100),
    rating_min: float | None = Query(None, ge=0, le=10),
    sort: str = Query("popularity", pattern="^(popularity|rating|newest)$"),
    page: int = Query(1, ge=1, le=500),
):
    """Discover movies using the website's bounded filter contract."""
    return await fetch_discover_movies(
        limit=limit,
        genre_id=genre_id,
        year_from=year_from,
        year_to=year_to,
        rating_min=rating_min,
        sort=sort,
        page=page,
    )
