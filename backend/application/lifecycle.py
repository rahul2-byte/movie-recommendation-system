"""Lazy application singletons for the bundle-backed recommendation service."""

from configuration.settings import settings
from infrastructure.metadata.movie_store import MovieStore
from observability.logging import get_logger
from serving.bundle_recommender import BundleRecommender
from serving.recommendation_pipeline import BundleRecommendationPipeline

log = get_logger(__name__)

_pipeline = None
_movie_store = None


def get_movie_store() -> MovieStore:
    """Create or return the process-local metadata store."""
    global _movie_store
    if _movie_store is None:
        log.info("Lifecycle: Initializing MovieStore (Lazy)...")
        # Lazy construction keeps module import cheap and lets warm Lambda
        # containers reuse the same metadata client across requests.
        _movie_store = MovieStore()

    return _movie_store


def get_pipeline() -> BundleRecommendationPipeline:
    """Create or return the validated bundle-backed recommendation pipeline."""
    global _pipeline
    if _pipeline is None:
        log.info("Lifecycle: Initializing Recommendation Pipeline...")

        # Load the bundle once at startup. Serving a different model release
        # per request would add latency and could mix incompatible artifacts.
        store = get_movie_store()

        bundle_dir = str(settings.MODEL_BUNDLE_DIR).strip()
        if bundle_dir:
            _pipeline = BundleRecommendationPipeline(
                BundleRecommender.load(bundle_dir), store
            )
            log.info("Lifecycle: Bundle-backed pipeline fully initialized.")
            return _pipeline

        raise RuntimeError("MODEL_BUNDLE_DIR is required for recommendation serving")
