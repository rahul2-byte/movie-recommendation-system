"""Movie metadata and search HTTP routes."""

from typing import Any

from application.lifecycle import get_movie_store
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/movies", tags=["Movies"])


@router.get("/search")
async def movie_search(
    q: str = Query(..., min_length=2),
    limit: int = Query(10, ge=5, le=20),
) -> list[dict]:
    """Search the operational metadata store by title or text query."""
    movie_store = get_movie_store()
    return await movie_store.search(q, limit)


@router.get("/{movie_id}")
async def get_movie_by_id(movie_id: int) -> dict[str, Any]:
    """
    Get movie details by TMDB ID.
    """
    movie_store = get_movie_store()
    movie = await movie_store.get(movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    return movie


@router.get("/tmdb/{tmdb_id}")
async def get_movie_by_tmdb_id(tmdb_id: int) -> dict[str, Any]:
    """Return one movie identified by its canonical TMDB ID."""
    movie = await get_movie_store().get(tmdb_id)
    if movie is None:
        raise HTTPException(status_code=404, detail="Movie not found")
    return movie
