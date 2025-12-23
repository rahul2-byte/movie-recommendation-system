from typing import Dict, List

from orchestrator.contracts import Candidate


def build_candidate_features(
    user_id: int,
    candidates: List[Candidate],
    labels: Dict[int, int],
) -> List[dict]:
    """
    Convert recall Candidates into flat ranking feature rows.

    One row = (user_id, item_id, features..., label)
    """

    rows: List[dict] = []

    for c in candidates:
        item_id = c.item_id

        row = {
            # -------------------------------------------------
            # Identifiers
            # -------------------------------------------------
            "user_id": int(user_id),
            "item_id": int(item_id),
            "query_id": int(user_id),  # for ranking models

            # -------------------------------------------------
            # Retriever flags
            # -------------------------------------------------
            "retrieved_by_two_tower": int("two_tower" in c.sources),
            "retrieved_by_als": int("als" in c.sources),
            "retrieved_by_item_cf": int("item_cf" in c.sources),
            "retrieved_by_content": int("content" in c.sources),

            # -------------------------------------------------
            # Retriever-local scores (0 if missing)
            # -------------------------------------------------
            "two_tower_score": float(c.scores.get("two_tower", 0.0)),
            "als_score": float(c.scores.get("als", 0.0)),
            "item_cf_score": float(c.scores.get("item_cf", 0.0)),
            "content_score": float(c.scores.get("content", 0.0)),

            # -------------------------------------------------
            # Cross-retriever signals
            # -------------------------------------------------
            "num_retrievers": int(len(c.sources)),

            # -------------------------------------------------
            # Label (pointwise)
            # -------------------------------------------------
            "label": int(labels.get(item_id, 0)),
        }

        rows.append(row)

    return rows
