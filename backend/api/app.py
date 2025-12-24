import logging
from fastapi import FastAPI, Depends, HTTPException

from api.schemas import (
    RecommendRequest,
    RecommendResponse,
)
from api.dependencies import load_inference_pipeline
from api.inference import RecommenderInference

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

app = FastAPI(
    title="Movie Recommendation API",
    version="1.0",
)


@app.on_event("startup")
def startup_event():
    LOGGER.info("Starting recommendation service")


@app.post(
    "/recommend",
    response_model=RecommendResponse,
)
def recommend(
    request: RecommendRequest,
    pipeline: RecommenderInference = Depends(load_inference_pipeline),
):
    if not request.seed_movie_ids and not request.preferred_genres:
        raise HTTPException(
            status_code=400,
            detail="At least one seed movie or genre must be provided",
        )

    recommendations = pipeline.recommend(
        seed_movie_ids=request.seed_movie_ids,
        preferred_genres=request.preferred_genres,
        top_k=request.top_k,
    )

    return {"recommendations": recommendations}
