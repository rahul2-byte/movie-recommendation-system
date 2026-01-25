from dotenv import load_dotenv
load_dotenv("./backend/.env")

import sys
from pathlib import Path
from typing import Dict, Iterator, List, Any

import logging
from multiprocessing import Pool, cpu_count, current_process
from functools import partial

import numpy as np
import pandas as pd

from orchestrator.orchestrator import RecallOrchestrator
from orchestrator.registry import RetrieverRegistry
from orchestrator.contracts import Candidate
from orchestrator.retrievers.two_tower import TwoTowerRetriever
from orchestrator.retrievers.content import ContentBasedRetriever
from orchestrator.retrievers.meta_based import MetaBasedRetriever
from orchestrator.retrievers.item_cf import ItemCFRetriever
from src.features.feature_builder import build_candidate_features
from src.features.feature_logger import FeatureLogger

from configs.settings import INTERACTIONS_PATH, OUTPUT_PATH, ITEM_META_PATH

# -------------------------------------------------
# CONFIG
# -------------------------------------------------
MIN_USER_INTERACTIONS = 5
RECENT_K = 5
# Adjust NUM_WORKERS based on your machine's core count and memory
NUM_WORKERS = 10

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)


# -------------------------------------------------
# WORKER-SCOPED VARIABLES
# -------------------------------------------------
# These will be initialized by init_worker() in each process
worker_orchestrator: RecallOrchestrator = None
worker_item_genres: dict = None
worker_item_stats: pd.DataFrame = None


# -------------------------------------------------
# WORKER INITIALIZER
# -------------------------------------------------
def init_worker():
    """
    Initializer for each worker process. Loads models and metadata once per process.
    """
    global worker_orchestrator, worker_item_genres, worker_item_stats
    worker_pid = current_process().pid
    LOGGER.info(f"[Worker {worker_pid}] Initializing...")

    # Load metadata once per worker
    LOGGER.info(f"[Worker {worker_pid}] Loading metadata.")
    item_meta = pd.read_parquet(ITEM_META_PATH)
    worker_item_genres = (
        item_meta.explode("genres")
        .groupby("movie_id")["genres"]
        .apply(set)
        .to_dict()
    )
    worker_item_stats = item_meta.set_index("movie_id")[
        ["vote_average", "vote_count", "release_year"]
    ]

    # Load models and build orchestrator once per worker
    LOGGER.info(f"[Worker {worker_pid}] Loading models and building orchestrator.")
    two_tower_user_emb = np.load("./backend/ml/models/two_tower/user_embeddings.npy")
    als_item_emb = np.load("./backend/ml/models/als/item_embeddings.npy")

    retrievers = [
        TwoTowerRetriever(
            model_dir=Path("./backend/ml/models/two_tower"),
            user_embeddings=two_tower_user_emb,
            index_path=Path("./backend/indices/two_tower"),
        ),
        MetaBasedRetriever(
            model_dir=Path("./backend/ml/models/meta_based"),
            index_path=Path("./backend/indices/meta_based"),
        ),
        ItemCFRetriever(
            model_dir=Path("./backend/ml/models/als"),
            item_embeddings=als_item_emb,
            index_path=Path("./backend/indices/als"),
        ),
        ContentBasedRetriever(
            model_dir=Path("./backend/ml/models/content_based"),
            index_path=Path("./backend/indices/content_based"),
        ),
    ]
    quotas = {
        "two_tower": 80,
        "item_cf": 60,
        "content": 60,
        "meta": 70,
    }
    retriever_registry = RetrieverRegistry(retrievers=retrievers, quotas=quotas)
    worker_orchestrator = RecallOrchestrator(retriever_registry)
    LOGGER.info(f"[Worker {worker_pid}] Initialization complete.")


# -------------------------------------------------
# STREAM USER CONTEXT
# -------------------------------------------------
def stream_user_context(
    interactions: pd.DataFrame,
) -> Iterator[Dict[str, Any]]:
    """
    Generator that yields user context for one user at a time, avoiding
    loading all user data into memory.
    """
    LOGGER.info("Building user interaction counts and identifying valid users.")
    interactions = interactions.sort_values("timestamp")
    user_interaction_counts = interactions.groupby("userId").size()
    valid_users = user_interaction_counts[
        user_interaction_counts >= MIN_USER_INTERACTIONS
    ].index

    LOGGER.info(f"Found {len(valid_users)} users with >= {MIN_USER_INTERACTIONS} interactions. Streaming contexts.")
    
    # Iterate through valid users and yield their context
    for user_id, user_df in interactions[interactions["userId"].isin(valid_users)].groupby("userId"):
        recent_items = user_df["movieId"].astype(int).tail(RECENT_K).tolist()
        heldout = set(user_df.iloc[5:]["movieId"].astype(int))
        
        yield {
            "user_id": int(user_id),
            "recent_items": recent_items,
            "num_interactions": user_interaction_counts[user_id],
            "heldout": heldout,
        }


# -------------------------------------------------
# WORKER FUNCTION
# -------------------------------------------------
def process_user(
    user_context: Dict[str, Any],
) -> List[dict]:
    """
    Processes a single user to generate features, using the pre-loaded
    models and metadata in the worker process.
    """
    user_id = user_context["user_id"]
    
    candidates = worker_orchestrator.recall(
        user_id=user_id,
        seen_item_ids=user_context["recent_items"],
    )

    labels = {i: 2 for i in user_context["heldout"]}

    # build_candidate_features returns a list of feature dicts (rows)
    feature_rows = build_candidate_features(
        user_id=user_id,
        candidates=candidates,
        labels=labels,
        user_recent_items=user_context["recent_items"],
        user_num_interactions=user_context["num_interactions"],
        item_genres=worker_item_genres,
        item_stats=worker_item_stats,
    )
    return feature_rows


# -------------------------------------------------
# MAIN
# -------------------------------------------------
if __name__ == "__main__":
    LOGGER.info("Loading interactions")
    interactions = pd.read_parquet(INTERACTIONS_PATH)

    # Get a generator for user contexts
    user_context_generator = stream_user_context(interactions)

    feature_logger = FeatureLogger(OUTPUT_PATH)
    total_users_processed = 0

    try:
        # The initializer loads models for each worker in the pool
        with Pool(processes=NUM_WORKERS, initializer=init_worker) as pool:
            # imap_unordered is memory-efficient as it processes the iterable (generator)
            # and doesn't store all results in memory.
            # chunksize tells the pool to grab N items from the generator at a time
            # to reduce IPC overhead.
            for feature_rows in pool.imap_unordered(process_user, user_context_generator, chunksize=50):
                if feature_rows:
                    feature_logger.write_rows(feature_rows)
                
                total_users_processed += 1
                if total_users_processed % 1000 == 0:
                    LOGGER.info(f"Processed {total_users_processed} users...")

    finally:
        feature_logger.close()

    LOGGER.info(f"Feature logging completed for {total_users_processed} users.")
