import asyncio
import sys
from pathlib import Path

# Add backend dir to sys.path
BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from pipeline.pipeline import RecommendationPipeline
from retrieval.inference.recall import RecallService
from ranking.inference.lgbm import LGBMRanker
from features.builder import FeatureBuilder
from common.services.movie_store import MovieStore
from common.config import config
from common.types import Query
from data.loader import load_movielens_movies, load_movielens_links

async def test_pipeline():
    print("Loading data...")
    movies_df = load_movielens_movies()
    links_df = load_movielens_links()
    
    print("Initializing services...")
    movie_store = MovieStore(movies_df, links_df)
    
    # 1. Feature Builder
    feature_builder = FeatureBuilder.from_paths(
        movies_path=config.system.movies_metadata_path,
        tags_path=config.system.tags_path
    )
    
    # 2. Recall Service
    recall_service = RecallService()
    
    # 3. Ranker
    model_path = Path(config.system.ranker_model_dir) / "lgbm_lambdarank.txt"
    ranker = LGBMRanker(model_path=str(model_path))
    
    # Instantiate pipeline
    pipeline = RecommendationPipeline(
        recall_service=recall_service,
        feature_builder=feature_builder,
        ranker=ranker,
        movie_store=movie_store,
    )
    
    # Toy Story (1), Jumanji (2), Heat (6), Sabrina (7), GoldenEye (10)
    seed_ids = [1, 2, 6, 7, 10]
    query = Query(seed_movie_ids=seed_ids)
    
    print(f"\nGetting recommendations for seed movies: {seed_ids}")
    recommendations = await pipeline.recommend(query, top_n=10)
    
    print("\nTop 10 Recommendations:")
    print("-" * 50)
    for i, rec in enumerate(recommendations):
        title = rec.get("title", "Unknown")
        movie_id = rec.get("movieId") # Fixed: Use movieId
        score = rec.get("score", 0.0)
        sources = ", ".join(rec.get("retrieval_sources", []))
        print(f"{i+1}. {title} (ID: {movie_id})")
        print(f"   Score: {score:.4f} | Sources: {sources}")
    print("-" * 50)

if __name__ == "__main__":
    asyncio.run(test_pipeline())