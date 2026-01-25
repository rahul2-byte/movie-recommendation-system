from typing import Dict, List, Set, Set

import numpy as np
import pandas as pd
import pandas as pd

from orchestrator.contracts import Candidate


# -------------------------------------------------
# Utilities
# -------------------------------------------------
def compute_ranks(scores: Dict[int, float]) -> Dict[int, int]:
    """
    Compute rank per item (1 = best).
    """
    if not scores:
        return {}

    items, values = zip(*scores.items())
    order = np.argsort(-np.array(values))
    ranks = np.empty_like(order)
    ranks[order] = np.arange(1, len(order) + 1)

    return {items[i]: int(ranks[i]) for i in range(len(items))}


# -------------------------------------------------
# Feature Builder
# -------------------------------------------------
def build_candidate_features(
    user_id: int,
    candidates: List[Candidate],
    labels: Dict[int, int],
    user_recent_items: List[int],
    user_num_interactions: int,
    item_stats: pd.DataFrame,
    item_genres: Dict[int, Set[str]],
) -> List[dict]:
    """
    Convert recall Candidates into ranking feature rows.
    """

    # -------------------------
    # Collect retriever scores
    # -------------------------
    score_maps = {
        "two_tower": {},
        "item_item": {},
        "meta": {},
        "content": {},
    }

    for c in candidates:
        for src, score in c.scores.items():
            if src == "als" or src == "item_cf":
                src = "item_item"
            score_maps[src][c.item_id] = score

    rank_maps = {
        k: compute_ranks(v) for k, v in score_maps.items()
    }

    # -------------------------
    # Precompute user genre profile
    # -------------------------
    user_genres: Set[str] = set()
    for item in user_recent_items:
        user_genres |= item_genres.get(item, set())

    user_genre_diversity = float(len(user_genres))

    rows: List[dict] = []

    for c in candidates:
        item_id = c.item_id

        stats = (
            item_stats.loc[item_id]
            if item_id in item_stats.index
            else None
        )

        avg_rating = float(stats.vote_average) if stats is not None else 0.0
        num_ratings = int(stats.vote_count) if stats is not None else 0
        release_year = (
            int(stats.release_year)
            if stats is not None and not pd.isna(stats.release_year)
            else 0
        )
        log_num_ratings = float(np.log1p(num_ratings))
        is_long_tail = int(num_ratings < 50)

        item_genre_set = item_genres.get(item_id, set())
        genre_overlap = len(item_genre_set & user_genres)
        genre_overlap_ratio = (
            genre_overlap / len(user_genres) if user_genres else 0.0
        )

        row = {
            # -------------------------
            # Identifiers
            # -------------------------
            "user_id": int(user_id),
            "item_id": int(item_id),

            # -------------------------
            # Retriever flags
            # -------------------------
            "retrieved_by_two_tower": int("two_tower" in c.sources),
            "retrieved_by_item_item": int(
                "item_cf" in c.sources or "als" in c.sources
            ),
            "retrieved_by_meta": int("meta" in c.sources),
            "retrieved_by_content": int("content" in c.sources),

            # -------------------------
            # Scores
            # -------------------------
            "two_tower_score": float(score_maps["two_tower"].get(item_id, 0.0)),
            "item_item_score": float(score_maps["item_item"].get(item_id, 0.0)),
            "meta_score": float(score_maps["meta"].get(item_id, 0.0)),
            "content_score": float(score_maps["content"].get(item_id, 0.0)),

            # -------------------------
            # Ranks
            # -------------------------
            "two_tower_rank": rank_maps["two_tower"].get(item_id, 999),
            "item_item_rank": rank_maps["item_item"].get(item_id, 999),
            "meta_rank": rank_maps["meta"].get(item_id, 999),
            "content_rank": rank_maps["content"].get(item_id, 999),

            # -------------------------
            # Cross retriever
            # -------------------------
            "num_retrievers": int(len(c.sources)),

            # -------------------------
            # Item metadata
            # -------------------------
            "avg_rating": avg_rating,
            "num_ratings": num_ratings,
            "log_num_ratings": log_num_ratings,
            "release_year": release_year,
            "is_long_tail": is_long_tail,

            # -------------------------
            # User aggregates
            # -------------------------
            "user_num_interactions": int(user_num_interactions),
            "user_genre_diversity": user_genre_diversity,

            # -------------------------
            # Interaction features
            # -------------------------
            "genre_overlap_ratio": genre_overlap_ratio,

            # -------------------------
            # Label (graded)
            # -------------------------
            "label": int(labels.get(item_id, 0)),
        }

        rows.append(row)

    return rows
