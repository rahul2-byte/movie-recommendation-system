import threading
from pathlib import Path

from data.loader import load_movielens_links, load_movies_metadata
from features.builder import FeatureBuilder
from pipeline.pipeline import RecommendationPipeline
from ranking.inference.lgbm import LGBMRanker
from retrieval.inference.recall import RecallService

from common.config import config
from common.logger import get_logger
from common.services.movie_store import MovieStore

log = get_logger(__name__)

_pipeline = None
_movie_store = None
_lock = threading.Lock()


def get_movie_store() -> MovieStore:
    global _movie_store
    if _movie_store is not None:
        return _movie_store
    with _lock:
        if _movie_store is None:
            log.info("Lifecycle: Initializing MovieStore (Lazy)...")
            enriched_df = load_movies_metadata()
            # Store raw enriched_df temporarily to share with FeatureBuilder
            links_df = load_movielens_links()
            _movie_store = MovieStore(
                enriched_df.rename(
                    columns={"movie_id": "movieId", "tmdb_id": "tmdbId"}
                ),
                links_df,
            )
            # Attach the original df for the FeatureBuilder to reuse
            _movie_store._raw_enriched_df = enriched_df
    return _movie_store


def get_pipeline() -> RecommendationPipeline:
    global _pipeline
    if _pipeline is not None:
        return _pipeline
    with _lock:
        if _pipeline is None:
            store = get_movie_store()
            # Use the shared raw df to avoid loading it twice from disk/S3
            log.info("Lifecycle: Initializing FeatureBuilder using shared memory...")
            feature_builder = FeatureBuilder.from_dataframe(
                movies_df=store._raw_enriched_df, tags_path=config.system.tags_path
            )
            recall_service = RecallService()
            model_path = Path(config.system.ranker_model_dir) / "lgbm_lambdarank.txt"
            ranker = LGBMRanker(model_path=str(model_path))
            _pipeline = RecommendationPipeline(
                recall_service, feature_builder, ranker, store
            )
            log.info("Lifecycle: Pipeline fully initialized.")
    return _pipeline
