from fastapi import APIRouter, Query, Request
from typing import List
import logging
import json

log = logging.getLogger(__name__)

router = APIRouter(prefix="/movies", tags=["Movies"])

@router.get("/search")
async def movie_search(
    request: Request,
    q: str = Query(..., min_length=2),
    limit: int = Query(10, ge=5, le=20),
) -> List[dict]:
    movie_store = request.app.state.movie_store
    results = await movie_store.search(q, limit)
    
    # Log the first result to check for anomalies or NaN values
    if results:
        try:
            # json.dumps will verify if it's serializable. 
            # If it contains Infinity or NaN, allow_nan=False will raise ValueError.
            log.info(f"Search results sample: {json.dumps(results[0], default=str, allow_nan=False)}")
        except ValueError as e:
            log.error(f"JSON Serialization Error (NaN/Infinity detected): {e}")
            log.error(f"Bad Result Object: {results[0]}")
    
    return results
