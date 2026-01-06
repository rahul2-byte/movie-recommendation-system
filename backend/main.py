from dotenv import load_dotenv
load_dotenv()
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.services.movie_index import load_movie_index
from api.recommend.movie_index import load_movies

from api.v1.catalog import router as catalog_router
from api.v1.movies import router as movies_router
from api.v1.recommend import router as recommend_router

from api.recommend.model_registry import get_lgbm_model

app = FastAPI(title="Movie Platform API")

@app.on_event("startup")
def startup():
    load_movies(Path("./backend/data/raw/movies.csv"))
    load_movie_index(
        Path("./backend/data/raw/movies.csv"),
        Path("./backend/data/raw/links.csv")
    )
    get_lgbm_model("./backend/models/ranker/lgbm_lambdarank.txt")

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