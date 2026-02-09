# backend/api/main.py
"""
Main FastAPI application to serve movie recommendations.
"""

from typing import List

from common.services.movie_store import MovieStore
from common.types import Candidate, Query
from data_io.data_loader import (
    load_movielens_links,
    load_movielens_movies,
    load_processed_ratings,
)
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from inference.pipeline import InferencePipeline
from pydantic import BaseModel

from api.v1.catalog import router as catalog_router
from api.v1.movies import router as movies_router
from api.v1.recommend import router as recommend_v1_router

# --- API Definition ---
app = FastAPI(
    title="Movie Recommendation API",
    description="A query-based movie recommendation system.",
    version="1.0.0",
)

# Add CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add routers
app.include_router(catalog_router, prefix="/api/v1")
app.include_router(movies_router, prefix="/api/v1")
app.include_router(recommend_v1_router, prefix="/api/v1")

# Also mount catalog at root for direct access as requested by frontend logs
app.include_router(catalog_router)


# --- Models ---
class RecommendRequest(BaseModel):
    seed_movie_ids: List[int]


class RecommendResponse(BaseModel):
    recommendations: List[Candidate]


# --- Application Startup ---
# Create a global instance of the inference pipeline to be reused across requests.
# This is crucial for performance as it pre-loads all models and data.
pipeline: InferencePipeline


@app.on_event("startup")
async def startup_event():
    """
    Initializes the InferencePipeline and MovieStore when the application starts.
    """
    global pipeline

    # Load data for MovieStore
    movies_df = load_movielens_movies()
    links_df = load_movielens_links()
    ratings_df = load_processed_ratings()

    # Instantiate services
    movie_store = MovieStore(movies_df, links_df, ratings_df)
    app.state.movie_store = movie_store

    pipeline = InferencePipeline()
    print("INFO:     Inference Pipeline and MovieStore initialized.")


# --- API Endpoints ---
import asyncio
import logging
import traceback

# Setup logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


@app.post(
    "/recommend"
)  # Removed response_model to avoid validation conflicts for now, or update it
async def recommend(request: RecommendRequest):
    """
    Generate movie recommendations based on a set of seed movies.
    """
    log.info(f"Received recommendation request with seeds: {request.seed_movie_ids}")

    if len(request.seed_movie_ids) == 0:
        raise HTTPException(status_code=400, detail="seed_movie_ids cannot be empty.")

    try:
        # Create a Query object from the request
        query = Query(seed_movie_ids=request.seed_movie_ids)

        # Get recommendations from the pipeline
        log.info("Running inference pipeline...")
        candidates = pipeline.recommend(query, top_n=20)
        log.info(f"Pipeline returned {len(candidates)} candidates.")

        # Enrich candidates with metadata
        movie_store = app.state.movie_store

        log.info("Enriching candidates with metadata (parallel)...")

        # Fetch all metadata in parallel
        tasks = [movie_store.get(candidate.movie_id) for candidate in candidates]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        enriched_results = []
        for i, result in enumerate(results):
            candidate = candidates[i]
            if isinstance(result, Exception):
                log.error(f"Error enriching movie {candidate.movie_id}: {result}")
                continue

            if result:
                # Add score from candidate
                result["score"] = candidate.score
                enriched_results.append(result)
            else:
                log.warning(f"Metadata not found for movie_id: {candidate.movie_id}")

        log.info(f"Returning {len(enriched_results)} enriched recommendations.")
        return {"recommendations": enriched_results}
    except Exception as e:
        # A generic error handler to catch issues during inference
        log.error(f"ERROR:    An error occurred during recommendation: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error.")


@app.get("/health")
def health():
    """
    A simple health check endpoint.
    """
    return {"status": "ok"}


# To run this application:
# uvicorn api.main:app --reload
