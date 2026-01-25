from fastapi import APIRouter, Request
from backend.api.schemas.recommend import RecommendRequest, RecommendResponse

import time
import uuid
from logger.services.mlflow_logger import log_recommendation, log_click

router = APIRouter(prefix="/recommend", tags=["recommend"])

@router.post("", response_model=RecommendResponse)
def recommend_movies(request: Request, payload: RecommendRequest):
    start = time.time()

    pipeline = request.app.state.recommendation_pipeline
    results = pipeline.run(
        seed_movie_ids=payload.seed_movie_ids,
        moods=payload.moods,
        limit=payload.limit,
    )

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