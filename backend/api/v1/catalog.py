from fastapi import APIRouter, Query
from infrastructure.metadata.catalog_service import (
    fetch_new_releases,
    fetch_popular_movies,
    fetch_trending_movies,
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
