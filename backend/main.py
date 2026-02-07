from dotenv import load_dotenv
load_dotenv()

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.v1.catalog import router as catalog_router
from api.v1.movies import router as movies_router
from api.v1.recommend import router as recommend_router

from pipeline.pipeline import RecommendationPipeline
from retrieval.inference.recall import RecallService
from ranking.inference.lgbm import LGBMRanker
from features.builder import FeatureBuilder
from common.services.movie_store import MovieStore
from common.config import config
from common.logger import get_logger
from data.loader import load_movielens_movies, load_movielens_links

from logger.background.tasks import start_background_tasks

from mangum import Mangum

log = get_logger(__name__)

app = FastAPI(title="Movie Platform API")

# Mangum handler for AWS Lambda
handler = Mangum(app)

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    log.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )

@app.get("/ping")
def ping():
    return {"status": "ok", "environment": config.settings.ENVIRONMENT}

@app.on_event("startup")
def startup():
    start_background_tasks()
    
    # Load data
    movies_df = load_movielens_movies()
    links_df = load_movielens_links()
    
    # Instantiate services
    movie_store = MovieStore(movies_df, links_df)
    
    # 1. Feature Builder (Loads genre/tag matrices)
    feature_builder = FeatureBuilder.from_paths(
        movies_path=config.system.movies_metadata_path,
        tags_path=config.system.tags_path
    )
    
    # 2. Recall Service (Loads retrieval models & FAISS indices)
    recall_service = RecallService()
    
    # 3. Ranker (Loads LGBM model)
    model_path = Path(config.system.ranker_model_dir) / "lgbm_lambdarank.txt"
    ranker = LGBMRanker(model_path=str(model_path))
    
    # Instantiate pipeline
    recommendation_pipeline = RecommendationPipeline(
        recall_service=recall_service,
        feature_builder=feature_builder,
        ranker=ranker,
        movie_store=movie_store,
    )
    
    # Store services in app state
    app.state.movie_store = movie_store
    app.state.recommendation_pipeline = recommendation_pipeline

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(movies_router, prefix="/api/v1")
app.include_router(recommend_router, prefix="/api/v1")
app.include_router(catalog_router, prefix="/api/v1")
