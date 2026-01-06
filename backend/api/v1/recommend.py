from unittest import result
from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import List, Literal
from api.schemas.recommend import RecommendRequest, RecommendResponse
from api.recommend.pipeline import RecommendationPipeline

router = APIRouter(prefix="/recommend", tags=["recommend"])
pipeline = RecommendationPipeline()


@router.post("", response_model=RecommendResponse)
def recommend_movies(payload: RecommendRequest):
    results = pipeline.run(
        seed_movie_ids=payload.seed_movie_ids,
        moods=payload.moods,
        limit=payload.limit,
    )
    return RecommendResponse(recommendations=results)