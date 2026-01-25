from fastapi import APIRouter, Query, Request
from typing import List

router = APIRouter(prefix="/movies", tags=["Movies"])

@router.get("/search")
def movie_search(
    request: Request,
    q: str = Query(..., min_length=2),
    limit: int = Query(10, ge=5, le=20),
) -> List[dict]:
    movie_store = request.app.state.movie_store
    return movie_store.search(q, limit)
