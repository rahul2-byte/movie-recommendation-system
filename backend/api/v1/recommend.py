from fastapi import APIRouter, Request
from api.schemas.recommend import RecommendRequest, RecommendResponse
from common.types import Query

import time
import uuid
from logger.services.mlflow_logger import log_recommendation, log_click

router = APIRouter(prefix="/recommend", tags=["recommend"])

@router.post("", response_model=RecommendResponse)
async def recommend_movies(request: Request, payload: RecommendRequest):
    start = time.time()

    from common.lifecycle import get_pipeline
    pipeline = get_pipeline()
    
    # We await the async recommend method
    results = await pipeline.recommend(
        query=Query(seed_movie_ids=payload.seed_movie_ids),
        top_n=payload.limit or 20,
    )

    # Map 'score' from pipeline to 'rating' expected by RecommendResponse schema
    for r in results:
        if "score" in r:
            r["rating"] = r["score"]

    latency = int((time.time() - start) * 1000)
    trace = {
        "request_id": str(uuid.uuid4()),
        "final_items": results,
        "latency_ms": latency,
    }

    log_recommendation(trace, latency)

    return RecommendResponse(recommendations=results)

@router.post("/click")
def movie_clicked():
    log_click()
    return {"status": "ok"}