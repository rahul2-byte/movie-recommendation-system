"""Recommendation and feedback HTTP routes."""

import logging
import time
import uuid

from fastapi import APIRouter, HTTPException, Query, Request

from api.schemas.recommend import RecommendRequest, RecommendResponse

router = APIRouter(prefix="/recommend", tags=["recommend"])
log = logging.getLogger(__name__)
PAGE_SIZE = 24


@router.post("", response_model=RecommendResponse)
async def recommend_movies(request: Request, payload: RecommendRequest):
    """Generate ranked recommendations for selected seed movies."""
    start = time.time()
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))

    log.info(
        "recommend.request.start request_id=%s seeds=%s limit=%s",
        request_id,
        payload.seed_tmdb_ids,
        payload.limit or 20,
    )

    try:
        from application.lifecycle import get_pipeline, get_recommendation_sessions

        pipeline = get_pipeline()

        ranked_candidates = await pipeline.rank_candidates(
            seed_tmdb_ids=payload.seed_tmdb_ids,
            top_n=payload.limit,
            refresh_seed=payload.refresh_seed,
        )
        session_id = get_recommendation_sessions().create(ranked_candidates)
        results, next_offset = await pipeline.materialize_candidates(
            ranked_candidates,
            offset=0,
            page_size=PAGE_SIZE,
        )

        latency = int((time.time() - start) * 1000)
        log.info(
            "recommend.request.success request_id=%s latency_ms=%s result_count=%s",
            request_id,
            latency,
            len(results),
        )

        return RecommendResponse(
            recommendations=results,
            sessionId=session_id,
            nextOffset=next_offset,
            hasMore=next_offset is not None,
        )
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


@router.get("/{session_id}", response_model=RecommendResponse)
async def get_recommendation_page(
    session_id: str,
    offset: int = Query(default=0, ge=0),
):
    """Return the next poster-backed page from an existing ranked lineup."""
    from application.lifecycle import get_pipeline, get_recommendation_sessions

    ranked_candidates = get_recommendation_sessions().get(session_id)
    if ranked_candidates is None:
        raise HTTPException(
            status_code=404,
            detail="This lineup has expired. Build a new one.",
        )

    results, next_offset = await get_pipeline().materialize_candidates(
        ranked_candidates,
        offset=offset,
        page_size=PAGE_SIZE,
    )
    return RecommendResponse(
        recommendations=results,
        sessionId=session_id,
        nextOffset=next_offset,
        hasMore=next_offset is not None,
    )
