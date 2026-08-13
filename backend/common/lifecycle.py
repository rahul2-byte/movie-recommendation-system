from configs.settings import settings
from serving.pipeline import BundleRecommendationPipeline
from serving.recommender import BundleRecommender

from common.logger import get_logger
from common.services.movie_store import MovieStore

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


def get_pipeline() -> BundleRecommendationPipeline:
    global _pipeline
    if _pipeline is not None:
        return _pipeline

    if _pipeline is None:
        log.info("Lifecycle: Initializing Recommendation Pipeline...")

        # 1. Store
        store = get_movie_store()

        bundle_dir = str(settings.MODEL_BUNDLE_DIR).strip()
        if bundle_dir:
            _pipeline = BundleRecommendationPipeline(
                BundleRecommender.load(bundle_dir), store
            )
            log.info("Lifecycle: Bundle-backed pipeline fully initialized.")
            return _pipeline

        raise RuntimeError("MODEL_BUNDLE_DIR is required for recommendation serving")
