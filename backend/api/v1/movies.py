from fastapi import APIRouter, Query
from typing import List
from api.services.movie_index import search_movies

router = APIRouter(prefix="/movies", tags=["Movies"])

@router.get("/search")
def movie_search(
    q: str = Query(..., min_length=2),
    limit: int = Query(10, ge=5, le=20),
) -> List[dict]:
    return search_movies(q, limit)
