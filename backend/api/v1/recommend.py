"""Recommendation and feedback HTTP routes."""

import logging
import time
import uuid

from fastapi import APIRouter, HTTPException, Request

from api.schemas.recommend import RecommendRequest, RecommendResponse

router = APIRouter(prefix="/recommend", tags=["recommend"])
log = logging.getLogger(__name__)


@router.post("", response_model=RecommendResponse)
async def recommend_movies(request: Request, payload: RecommendRequest):
    """Generate ranked recommendations for selected seed movies."""
    start = time.time()
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))

    log.info(
        "recommend.request.start request_id=%s seeds=%s limit=%s moods=%s",
        request_id,
        payload.seed_tmdb_ids,
        payload.limit or 20,
        payload.moods,
    )

    try:
        from application.lifecycle import get_pipeline

        pipeline = get_pipeline()

        # We await the async recommend method
        results = await pipeline.recommend(
            seed_tmdb_ids=payload.seed_tmdb_ids,
            top_n=payload.limit or 20,
        )

        latency = int((time.time() - start) * 1000)
        log.info(
            "recommend.request.success request_id=%s latency_ms=%s result_count=%s",
            request_id,
            latency,
            len(results),
        )

        return RecommendResponse(recommendations=results)
    except Exception as e:
        latency = int((time.time() - start) * 1000)
        log.exception(
            "recommend.request.failed request_id=%s latency_ms=%s error=%s",
            request_id,
            latency,
            str(e),
        )
        raise HTTPException(
            status_code=500,
            detail=f"Recommendation failed. request_id={request_id}",
        ) from e
