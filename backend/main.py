from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.v1.catalog import router as catalog_router
from backend.api.v1.movies import router as movies_router
from backend.api.v1.recommend import router as recommend_router

from backend.ml.recommend.pipeline import RecommendationPipeline
from backend.ml.recommend.recall_service import RecallService
from backend.ml.recommend.lgbm_ranker import LGBMRanker
from backend.services.movie_store import MovieStore
from backend.io.data_loader import load_movielens_movies, load_movielens_links

from logger.background.tasks import start_background_tasks

app = FastAPI(title="Movie Platform API")

@app.on_event("startup")
def startup():
    start_background_tasks()
    
    # Load data
    movies_df = load_movielens_movies()
    links_df = load_movielens_links()
    
    # Instantiate services
    movie_store = MovieStore(movies_df, links_df)
    recall_service = RecallService()
    ranker = LGBMRanker(model_path="./backend/ml/models/ranker/lgbm_lambdarank.txt")
    
    # Instantiate pipeline
    recommendation_pipeline = RecommendationPipeline(
        recall_service=recall_service,
        ranker=ranker,
        movie_store=movie_store,
    )
    
    # Store services in app state
    app.state.movie_store = movie_store
    app.state.recommendation_pipeline = recommendation_pipeline

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(movies_router, prefix="/api/v1")
app.include_router(recommend_router, prefix="/api/v1")
app.include_router(catalog_router, prefix="/api/v1")
