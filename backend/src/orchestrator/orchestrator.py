import logging
from dataclasses import dataclass
from typing import Dict, List, Iterable, Optional, Set

from .registry import RetrieverRegistry
from .contracts import Candidate
from .blending.normalization import normalize_scores
from .blending.quota import apply_quota
from .blending.dedup import deduplicate
from .filters.seen_items import filter_seen_items

LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------
# Config
# ---------------------------------------------------------
OVERFETCH_MULTIPLIER = 3  # fetch more than quota to survive filtering


# ---------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------
class RecallOrchestrator:
    """
    Multi-retriever recall orchestrator.

    Responsibilities:
    - Query all active retrievers
    - Normalize retriever-local scores
    - Enforce recall quotas
    - Deduplicate candidates
    - Filter seen items

    DOES NOT:
    - Rank items
    - Apply business logic
    - Compare raw retriever scores
    """

    def __init__(
        self,
        registry: RetrieverRegistry,
    ) -> None:
        self.registry = registry

    def recall(
        self,
        user_id: int,
        seen_item_ids: Optional[Iterable[int]] = None,
    ) -> List[Candidate]:
        """
        Generate recall candidates for a user.

        Args:
            user_id: external user identifier
            seen_item_ids: items already interacted with

        Returns:
            List[Candidate] (unordered)
        """
        LOGGER.info("Starting recall for user_id=%s", user_id)

        seen_set: Set[int] = set(seen_item_ids) if seen_item_ids else set()

        all_candidates: List[Candidate] = []

        # -------------------------------------------------
        # 1. Query each retriever independently
        # -------------------------------------------------
        for retriever in self.registry.active_retrievers():
            name = retriever.name
            quota = self.registry.quota(name)

            fetch_k = quota * OVERFETCH_MULTIPLIER

            LOGGER.debug(
                "Querying retriever=%s fetch_k=%d quota=%d",
                name,
                fetch_k,
                quota,
            )

            if retriever.name == "item_cf":
                results = retriever.retrieve(
                    user_id=user_id,
                    top_k=fetch_k,
                    recent_item_ids=seen_set,
                )
            else:
                results = retriever.retrieve(
                    user_id=user_id,
                    top_k=fetch_k,
                )

            if not results:
                LOGGER.warning("Retriever=%s returned no results", name)
                continue

            # results: List[(item_id, raw_score)]
            item_ids, raw_scores = zip(*results)

            # -------------------------------------------------
            # 2. Normalize scores (retriever-local)
            # -------------------------------------------------
            norm_scores = normalize_scores(raw_scores)

            candidates = [
                Candidate(
                    item_id=int(item_id),
                    sources=[name],
                    scores={name: float(score)},
                )
                for item_id, score in zip(item_ids, norm_scores)
            ]

            # -------------------------------------------------
            # 3. Apply quota
            # -------------------------------------------------
            candidates = apply_quota(
                candidates=candidates,
                quota=quota,
            )

            LOGGER.info(
                "Retriever=%s produced %d candidates",
                name,
                len(candidates),
            )

            all_candidates.extend(candidates)

        # -------------------------------------------------
        # 4. Deduplicate across retrievers
        # -------------------------------------------------
        LOGGER.info("Deduplicating %d candidates", len(all_candidates))

        merged = deduplicate(all_candidates)

        # -------------------------------------------------
        # 5. Filter seen items
        # -------------------------------------------------
        if seen_set:
            merged = filter_seen_items(merged, seen_set)

        LOGGER.info(
            "Recall completed: %d final candidates",
            len(merged),
        )

        return merged
