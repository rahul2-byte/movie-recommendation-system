from dotenv import load_dotenv
load_dotenv("./backend/.env")

import sys
from pathlib import Path
from typing import Dict, Iterator

import logging

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

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)


# -------------------------------------------------
# LOAD METADATA (ONCE)
# -------------------------------------------------
# Load all metadata
item_meta = pd.read_parquet(ITEM_META_PATH)

# Build a separate item_genres dictionary
item_genres = (
    item_meta.explode("genres")
    .groupby("movie_id")["genres"]
    .apply(set)
    .to_dict()
)

# Build item_stats DataFrame (extract relevant columns for stats)
item_stats = item_meta.set_index("movie_id")[
    ["vote_average", "vote_count", "release_year"]
]


# -------------------------------------------------
# PREP USER CONTEXT
# -------------------------------------------------
def build_user_context(
    interactions: pd.DataFrame,
) -> Dict[int, Dict]:
    interactions = interactions.sort_values("timestamp")
    ctx = {}

    for user_id, df_u in interactions.groupby("userId"):
        if len(df_u) < MIN_USER_INTERACTIONS:
            continue

        ctx[int(user_id)] = {
            "recent_items": (
                df_u["movieId"]
                .astype(int)
                .tail(RECENT_K)
                .tolist()
            ),
            "num_interactions": len(df_u),
            "heldout": set(df_u.iloc[5:]["movieId"].astype(int)),
        }

    return ctx


# -------------------------------------------------
# MAIN
# -------------------------------------------------
if __name__ == "__main__":
    LOGGER.info("Loading interactions")
    interactions = pd.read_parquet(INTERACTIONS_PATH)

    user_ctx = build_user_context(interactions)

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
    orchestrator = RecallOrchestrator(retriever_registry)

    feature_logger = FeatureLogger(OUTPUT_PATH)

    def row_generator() -> Iterator[dict]:
        for user_id, ctx in user_ctx.items():
            candidates = orchestrator.recall(
                user_id=user_id,
                seen_item_ids=ctx["recent_items"],
            )

            labels = {i: 2 for i in ctx["heldout"]}

            yield from build_candidate_features(
                user_id=user_id,
                candidates=candidates,
                labels=labels,
                user_recent_items=ctx["recent_items"],
                user_num_interactions=ctx["num_interactions"],
                item_genres=item_genres,
                item_stats=item_stats,
            )

    feature_logger.write_stream(row_generator())

    LOGGER.info("Feature logging completed")
