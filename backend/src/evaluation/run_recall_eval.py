import logging
from typing import Dict, Set, List, Tuple, Optional, Iterable
from collections import defaultdict
from pathlib import Path
from functools import lru_cache

import pandas as pd
import numpy as np

from evaluation.recall_evaluator import RecallEvaluator

from orchestrator.retrievers.two_tower import TwoTowerRetriever
from orchestrator.retrievers.content import ContentBasedRetriever
from orchestrator.retrievers.als import ALSRetriever
from orchestrator.retrievers.item_cf import ItemCFRetriever
from orchestrator.registry import RetrieverRegistry
from orchestrator.orchestrator import RecallOrchestrator
from orchestrator.contracts import Candidate

# -------------------------------------------------------------------
# CONFIG
# -------------------------------------------------------------------
INTERACTIONS_PATH = "data/raw/ratings.csv"
MIN_USER_INTERACTIONS = 5
K_VALUES = [10, 50, 100]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# LOAD EMBEDDINGS (SINGLE SOURCE OF TRUTH)
# -------------------------------------------------------------------
two_tower_user_embeddings = np.load("models/two_tower/user_embeddings.npy")

als_user_embeddings = np.load("models/als/user_embeddings.npy")
als_item_embeddings = np.load("models/als/item_embeddings.npy")

# -------------------------------------------------------------------
# INSTANTIATE RETRIEVERS (ONE INDEX PER RETRIEVER)
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
# CANDIDATE QUOTAS (RECALL BUDGETING)
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

# -------------------------------------------------------------------
# TEMPORAL SPLIT + HOLDOUT
# -------------------------------------------------------------------
def build_eval_users(
    interactions: pd.DataFrame,
    recent_k: int = 5,
) -> Tuple[
    Dict[int, Set[int]],
    Dict[int, int],
    Dict[int, List[int]],
]:
    """
    Returns:
    - eval_users: user_id -> {held_out_item}
    - item_interaction_counts: item_id -> train-only interaction count
    - user_recent_items: user_id -> [recent_item_ids]
    """

    interactions = interactions.sort_values("timestamp")

    eval_users: Dict[int, Set[int]] = {}
    item_interaction_counts: Dict[int, int] = defaultdict(int)
    user_recent_items: Dict[int, List[int]] = {}

    for user_id, df_u in interactions.groupby("userId"):
        if len(df_u) < MIN_USER_INTERACTIONS:
            continue

        train_df = df_u.iloc[:-1]
        heldout_item = int(df_u.iloc[-1]["movieId"])

        eval_users[int(user_id)] = {heldout_item}

        # last K items from training history
        recent_items = (
            train_df["movieId"]
            .astype(int)
            .tail(recent_k)
            .tolist()
        )
        user_recent_items[int(user_id)] = recent_items

        for item_id in train_df["movieId"].values:
            item_interaction_counts[int(item_id)] += 1

    return eval_users, item_interaction_counts, user_recent_items



@lru_cache(maxsize=10_000)
def _orchestrator_call(
    user_id: int
) -> List[Candidate]:
    recent_items = user_recent_items.get(user_id, [])
    return orchestrator.recall(
        user_id=user_id,
        seen_item_ids=recent_items,
    )


def _extract_items(
    user_id: int,
    retriever_name: str,
) -> List[int]:
    candidates = _orchestrator_call(user_id)

    return [
        c.item_id
        for c in candidates
        if retriever_name in c.sources
    ]


def two_tower_retriever(user_id: int) -> List[int]:
    return _extract_items(user_id, "two_tower")


def als_retriever(user_id: int) -> List[int]:
    return _extract_items(user_id, "als")


def item_item_retriever(user_id: int) -> List[int]:
    return _extract_items(user_id, "als")


def content_retriever(user_id: int) -> List[int]:
    return _extract_items(user_id, "content")

# -------------------------------------------------------------------
# MAIN
# -------------------------------------------------------------------
if __name__ == "__main__":
    logger.info("Loading interaction data")

    interactions = pd.read_csv(
        INTERACTIONS_PATH,
        usecols=["userId", "movieId", "timestamp"],
    )

    eval_users, item_interaction_counts, user_recent_items = build_eval_users(interactions)

    total_items = len(item_interaction_counts)

    retriever_fns = {
        "two_tower": two_tower_retriever,
        "als": als_retriever,
        "item_item": item_item_retriever,
        "content": content_retriever,
    }

    evaluator = RecallEvaluator(
        retrievers=retriever_fns,
        k_values=K_VALUES,
        item_interaction_counts=item_interaction_counts,
        total_items=total_items,
    )

    logger.info("Starting offline recall evaluation")
    results = evaluator.evaluate(eval_users)

    logger.info("===== OFFLINE RECALL RESULTS =====")
    for model, metrics in results.items():
        logger.info("Model=%s", model)
        for metric, value in metrics.items():
            logger.info("  %s: %.4f", metric, value)
