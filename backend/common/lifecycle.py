import threading
from pathlib import Path

from common.config import config
from common.logger import get_logger
from common.services.movie_store import MovieStore
from features.builder import FeatureBuilder
from pipeline.pipeline import RecommendationPipeline
from ranking.inference.lgbm import LGBMRanker
from retrieval.inference.recall import RecallService

log = get_logger(__name__)

_pipeline = None
_movie_store = None


def get_movie_store() -> MovieStore:
    global _movie_store
    if _movie_store is not None:
        return _movie_store
        
    if _movie_store is None:
        log.info("Lifecycle: Initializing MovieStore (Lazy)...")
        # MovieStore now connects to DynamoDB internally
        _movie_store = MovieStore()
        
    return _movie_store


def get_pipeline() -> RecommendationPipeline:
    global _pipeline
    if _pipeline is not None:
        return _pipeline
        
    if _pipeline is None:
        log.info("Lifecycle: Initializing Recommendation Pipeline...")
        
        # 1. Store
        store = get_movie_store()
        
        # 2. Feature Builder (Stateless)
        feature_builder = FeatureBuilder()
        
        # 3. Recall Service (Lazy Init)
        recall_service = RecallService()
        
        # 4. Ranker
        ranker = LGBMRanker()
        
        # 5. Pipeline
        _pipeline = RecommendationPipeline(
            recall_service=recall_service,
            feature_builder=feature_builder,
            ranker=ranker,
            movie_store=store
        )
        log.info("Lifecycle: Pipeline fully initialized.")
        
    return _pipeline
