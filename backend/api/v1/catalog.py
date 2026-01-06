from fastapi import APIRouter, Query
from api.services.tmdb_catalog_service import (
    fetch_trending_movies,
    fetch_popular_movies,
    fetch_new_releases,
)

router = APIRouter(prefix="/api/v1/catalog", tags=["catalog"])


@router.get("/trending")
def trending(limit: int = Query(20, ge=5, le=50)):
    return fetch_trending_movies(limit)


@router.get("/popular")
def popular(limit: int = Query(20, ge=5, le=50)):
    return fetch_popular_movies(limit)


@router.get("/new")
def new_releases(limit: int = Query(20, ge=5, le=50)):
    return fetch_new_releases(limit)
