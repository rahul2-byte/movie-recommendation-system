import time
from collections import defaultdict
from typing import List, Dict

from reranking.config import (
    TOP_K_FINAL,
    CANDIDATE_POOL,
    MAX_ITEMS_PER_GENRE,
    MAX_ITEMS_PER_FRANCHISE,
    FRESHNESS_HALF_LIFE_DAYS,
    FRESHNESS_WEIGHT,
    GENRE_FIELD,
    FRANCHISE_FIELD,
    RELEASE_TS_FIELD,
)
from reranking.freshness import freshness_score
from reranking.diversity import can_add_item


class Reranker:
    """
    Deterministic post-ranking re-ranker enforcing:
    - diversity constraints
    - freshness bias
    """

    def rerank(
        self,
        ranked_items: List[dict],
    ) -> List[dict]:
        """
        ranked_items: sorted by model score DESC
        """
        now_ts = int(time.time())

        # Limit pool for efficiency
        pool = ranked_items[:CANDIDATE_POOL]

        # Apply freshness boost
        for item in pool:
            f_score = freshness_score(
                release_ts=item.get(RELEASE_TS_FIELD),
                now_ts=now_ts,
                half_life_days=FRESHNESS_HALF_LIFE_DAYS,
            )
            item["rerank_score"] = (
                item["score"] * (1.0 - FRESHNESS_WEIGHT)
                + f_score * FRESHNESS_WEIGHT
            )

        # Sort by adjusted score
        pool.sort(key=lambda x: x["rerank_score"], reverse=True)

        # Greedy diversity selection
        selected: List[dict] = []
        genre_counts = defaultdict(int)
        franchise_counts = defaultdict(int)

        for item in pool:
            if len(selected) >= TOP_K_FINAL:
                break

            if not can_add_item(
                item=item,
                genre_counts=genre_counts,
                franchise_counts=franchise_counts,
                max_per_genre=MAX_ITEMS_PER_GENRE,
                max_per_franchise=MAX_ITEMS_PER_FRANCHISE,
            ):
                continue

            selected.append(item)

            for g in item.get(GENRE_FIELD, []):
                genre_counts[g] += 1

            franchise = item.get(FRANCHISE_FIELD)
            if franchise:
                franchise_counts[franchise] += 1

        return selected
