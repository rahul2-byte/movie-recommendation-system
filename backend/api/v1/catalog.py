from fastapi import APIRouter, Query
from common.services.tmdb_catalog_service import (
    fetch_trending_movies,
    fetch_popular_movies,
    fetch_new_releases,
)

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/trending")
async def trending(limit: int = Query(20, ge=5, le=50)):
    return await fetch_trending_movies(limit)


@router.get("/popular")
async def popular(limit: int = Query(20, ge=5, le=50)):
    return await fetch_popular_movies(limit)


@router.get("/new")
async def new_releases(limit: int = Query(20, ge=5, le=50)):
    return await fetch_new_releases(limit)
