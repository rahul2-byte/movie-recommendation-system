import logging
import time
import uuid

from common.types import Query
from fastapi import APIRouter, HTTPException, Request
from logger.services.mlflow_logger import log_click, log_recommendation

from api.schemas.recommend import RecommendRequest, RecommendResponse

router = APIRouter(prefix="/recommend", tags=["recommend"])
log = logging.getLogger(__name__)


@router.post("", response_model=RecommendResponse)
async def recommend_movies(request: Request, payload: RecommendRequest):
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
            query=Query(seed_tmdb_ids=payload.seed_tmdb_ids),
            top_n=payload.limit or 20,
            request_id=request_id,
        )

        # Map 'score' from pipeline to 'rating' expected by RecommendResponse schema
        for r in results:
            if "score" in r:
                r["rating"] = r["score"]

        latency = int((time.time() - start) * 1000)
        trace = {
            "request_id": request_id,
            "final_items": results,
            "latency_ms": latency,
        }

        log_recommendation(trace, latency)
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


@router.post("/click")
def movie_clicked():
    log_click()
    return {"status": "ok"}
