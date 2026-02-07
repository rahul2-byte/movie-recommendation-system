import asyncio
import sys
import time
import os
import logging
import pandas as pd
import argparse
from pathlib import Path

# Force LOCAL environment for testing
os.environ["ENVIRONMENT"] = "LOCAL"

# Add backend to sys.path
BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(name)s | %(levelname)s | %(message)s')
log = logging.getLogger("test_runner")

from pipeline.pipeline import RecommendationPipeline
from retrieval.inference.recall import RecallService
from ranking.inference.lgbm import LGBMRanker
from features.builder import FeatureBuilder
from common.services.movie_store import MovieStore
from common.config import config
from common.types import Query
from data.loader import load_movies_metadata

class Timer:
    def __init__(self, name):
        self.name = name
    def __enter__(self):
        self.start = time.time()
        return self
    def __exit__(self, *args):
        self.end = time.time()
        self.interval = (self.end - self.start) * 1000
        log.info(f"[{self.name}] {self.interval:.2f} ms")

async def setup_pipeline():
    log.info("--- 1. Initialization ---")
    with Timer("Total Initialization"):
        with Timer("Load Metadata"):
            movies_enriched = load_movies_metadata()
            movies_df = movies_enriched.rename(columns={"movie_id": "movieId", "tmdb_id": "tmdbId"})
            movies_df["genres"] = movies_df["genres"].apply(lambda x: "|".join(x) if isinstance(x, list) else str(x))
            links_df = movies_df[["movieId", "tmdbId"]].copy()
            movies_df = movies_df.drop(columns=["tmdbId"])

        with Timer("MovieStore Init"):
            movie_store = MovieStore(movies_df, links_df)

        with Timer("FeatureBuilder Init"):
            feature_builder = FeatureBuilder.from_paths(
                movies_path=config.system.movies_metadata_path,
                tags_path=config.system.tags_path
            )

        with Timer("RecallService Init"):
            recall_service = RecallService()

        with Timer("Ranker Init"):
            ranker_path = Path(config.system.ranker_model_dir) / "lgbm_lambdarank.txt"
            ranker = LGBMRanker(model_path=str(ranker_path))

        pipeline = RecommendationPipeline(
            recall_service=recall_service,
            feature_builder=feature_builder,
            ranker=ranker,
            movie_store=movie_store,
        )
        
    return pipeline, recall_service, feature_builder, ranker, movie_store

async def run_functional_test(pipeline, query):
    log.info("\n--- 2. Functional Test ---")
    log.info(f"Getting recommendations for seed movies: {query.seed_movie_ids}")
    
    with Timer("Functional Request"):
        recommendations = await pipeline.recommend(query, top_n=10)
    
    if not recommendations:
        log.error("FAIL: No results returned.")
        return False

    print("\nTop 10 Recommendations:")
    print("-" * 50)
    for i, rec in enumerate(recommendations):
        title = rec.get("title", "Unknown")
        movie_id = rec.get("movieId")
        score = rec.get("score", 0.0)
        sources = ", ".join(rec.get("retrieval_sources", []))
        print(f"{i+1}. {title} (ID: {movie_id})")
        print(f"   Score: {score:.4f} | Sources: {sources}")
    print("-" * 50)
    
    return True

async def run_benchmark(pipeline, query):
    log.info("\n--- 3. Performance Benchmark ---")
    log.info("Running 5 warm-up requests to measure average latency...")
    
    latencies = []
    for i in range(5):
        s = time.time()
        await pipeline.recommend(query, top_n=10)
        dur = (time.time() - s) * 1000
        latencies.append(dur)
        log.info(f"Request {i+1}: {dur:.2f} ms")
        
    avg_latency = sum(latencies) / len(latencies)
    log.info(f"Average Warm Latency: {avg_latency:.2f} ms")
    
    if avg_latency > 500:
        log.warning(f"PERFORMANCE WARNING: Avg latency {avg_latency:.2f} ms > 500ms benchmark.")
    else:
        log.info(f"PERFORMANCE PASS: Avg latency {avg_latency:.2f} ms is within limits.")

async def run_granular_profile(recall_service, feature_builder, ranker, movie_store, query):
    log.info("\n--- 4. Deep Profiling (Breakdown) ---")
    
    # A. Recall
    with Timer("Stage 1: Retrieval (Total)"):
        candidates = await recall_service.recall(query, top_k=500)
    log.info(f"  > Retrieved {len(candidates)} candidates")

    # B. Feature Build
    with Timer("Stage 2: Feature Building"):
        features_input_df = pd.DataFrame({
            "query_movie_ids": [query.seed_movie_ids] * len(candidates),
            "candidate_movie_id": [c.movie_id for c in candidates]
        })
        features = feature_builder.build_features(features_input_df)
    
    # C. Ranking
    with Timer("Stage 3: Ranking"):
        top_candidates = ranker.rank(candidates, features, limit=10)

    # D. Enrichment
    with Timer("Stage 4: Enrichment"):
        results = []
        for c in top_candidates:
            meta = await movie_store.get(c.movie_id)
            if meta:
                meta["score"] = c.rank_score
                meta["retrieval_sources"] = c.sources
                results.append(meta)
                
    log.info("Deep profiling complete.")

async def main():
    parser = argparse.ArgumentParser(description="Run tests for the recommendation engine.")
    parser.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 6, 7, 10], help="Seed movie IDs")
    args = parser.parse_args()

    pipeline, recall_service, feature_builder, ranker, movie_store = await setup_pipeline()
    
    query = Query(seed_movie_ids=args.seeds)
    
    # Run all tests in sequence
    success = await run_functional_test(pipeline, query)
    if not success:
        sys.exit(1)
        
    await run_benchmark(pipeline, query)
    await run_granular_profile(recall_service, feature_builder, ranker, movie_store, query)

if __name__ == "__main__":
    asyncio.run(main())
