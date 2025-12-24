import logging
from pathlib import Path
from typing import Dict, List, Set, Tuple, Iterator

import pandas as pd
import numpy as np

from orchestrator.orchestrator import RecallOrchestrator
from orchestrator.registry import RetrieverRegistry
from orchestrator.contracts import Candidate

from orchestrator.retrievers.two_tower import TwoTowerRetriever
from orchestrator.retrievers.content import ContentBasedRetriever
from orchestrator.retrievers.als import ALSRetriever
from orchestrator.retrievers.item_cf import ItemCFRetriever

from features.feature_builder import build_candidate_features
from features.feature_logger import FeatureLogger


# -------------------------------------------------
# CONFIG
# -------------------------------------------------
INTERACTIONS_PATH = "data/raw/ratings.csv"
OUTPUT_PATH = "data/processed/ranking_features.parquet"

MIN_USER_INTERACTIONS = 5
RECENT_K = 5

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)


# -------------------------------------------------
# TEMPORAL SPLIT + USER CONTEXT
# -------------------------------------------------
def build_feature_logging_inputs(
    interactions: pd.DataFrame,
) -> Tuple[
    Dict[int, Set[int]],
    Dict[int, List[int]],
]:
    """
    Returns:
    - eval_users: user_id -> {held_out_item}
    - user_recent_items: user_id -> [recent train-only items]
    """
    interactions = interactions.sort_values("timestamp")

    eval_users: Dict[int, Set[int]] = {}
    user_recent_items: Dict[int, List[int]] = {}

    for user_id, df_u in interactions.groupby("userId"):
        if len(df_u) < MIN_USER_INTERACTIONS:
            continue

        train_df = df_u.iloc[:-1]
        heldout_item = int(df_u.iloc[-1]["movieId"])

        eval_users[int(user_id)] = {heldout_item}

        user_recent_items[int(user_id)] = (
            train_df["movieId"]
            .astype(int)
            .tail(RECENT_K)
            .tolist()
        )

    LOGGER.info(
        "Prepared feature logging inputs | users=%d",
        len(eval_users),
    )
    return eval_users, user_recent_items


# -------------------------------------------------------------------
# LOAD EMBEDDINGS
# -------------------------------------------------------------------
two_tower_user_embeddings = np.load(
    "models/two_tower/user_embeddings.npy"
)
als_user_embeddings = np.load(
    "models/als/user_embeddings.npy"
)
als_item_embeddings = np.load(
    "models/als/item_embeddings.npy"
)


# -------------------------------------------------------------------
# INSTANTIATE RETRIEVERS
# -------------------------------------------------------------------
retriever_objects = [
    TwoTowerRetriever(
        model_dir=Path("models/two_tower"),
        user_embeddings=two_tower_user_embeddings,
        index_path=Path("src/indices/two_tower"),
    ),
    ALSRetriever(
        model_dir=Path("models/als"),
        user_embeddings=als_user_embeddings,
        index_path=Path("src/indices/als"),
    ),
    ItemCFRetriever(
        model_dir=Path("models/als"),
        item_embeddings=als_item_embeddings,
        index_path=Path("src/indices/als"),
    ),
    ContentBasedRetriever(
        model_dir=Path("models/content_based"),
        index_path=Path("src/indices/content_based"),
    ),
]

# -------------------------------------------------------------------
# CANDIDATE QUOTAS
# -------------------------------------------------------------------
quotas = {
    "two_tower": 80,
    "als": 60,
    "item_cf": 40,
    "content": 40,
}

registry = RetrieverRegistry(
    retrievers=retriever_objects,
    quotas=quotas,
)

orchestrator = RecallOrchestrator(registry)


# -------------------------------------------------
# STREAMING ROW GENERATOR (CRITICAL)
# -------------------------------------------------
def row_generator(
    eval_users: Dict[int, Set[int]],
    user_recent_items: Dict[int, List[int]],
) -> Iterator[dict]:
    """
    Lazily yields ranking feature rows (NO accumulation).
    """
    for user_id, clicked_items in eval_users.items():
        recent_items = user_recent_items.get(user_id, [])

        candidates: List[Candidate] = orchestrator.recall(
            user_id=user_id,
            seen_item_ids=recent_items,
        )

        if not candidates:
            continue

        labels: Dict[int, int] = {
            item_id: 1 for item_id in clicked_items
        }

        for row in build_candidate_features(
            user_id=user_id,
            candidates=candidates,
            labels=labels,
        ):
            yield row


# -------------------------------------------------
# MAIN
# -------------------------------------------------
if __name__ == "__main__":
    LOGGER.info("Loading interaction data")

    interactions = pd.read_csv(
        INTERACTIONS_PATH,
        usecols=["userId", "movieId", "timestamp"],
    )

    eval_users, user_recent_items = build_feature_logging_inputs(
        interactions
    )

    feature_logger = FeatureLogger(
        output_path=OUTPUT_PATH,
        chunk_size=500_000,  # safe default
    )

    feature_logger.write_stream(
        row_generator(eval_users, user_recent_items)
    )

    LOGGER.info(
        "Feature logging completed | path=%s",
        OUTPUT_PATH,
    )
