from typing import List

import numpy as np
import lightgbm as lgb

from orchestrator.orchestrator import RecallOrchestrator
from orchestrator.contracts import Candidate
from reranking.reranker import Reranker


class RecommenderInference:
    def __init__(
        self,
        orchestrator: RecallOrchestrator,
        ranker: lgb.Booster,
        reranker: Reranker,
        feature_columns: List[str],
    ) -> None:
        self.orchestrator = orchestrator
        self.ranker = ranker
        self.reranker = reranker
        self.feature_columns = feature_columns

    def recommend(
        self,
        seed_movie_ids: List[int],
        preferred_genres: List[str],
        top_k: int,
    ) -> List[dict]:
        # -------------------------------------------------
        # 1️⃣ Recall (seed-driven, cold-start)
        # -------------------------------------------------
        candidates: List[Candidate] = self.orchestrator.recall(
            user_id=-1,  # dummy, not used
            seen_item_ids=seed_movie_ids,
        )

        if not candidates:
            return []

        # -------------------------------------------------
        # 2️⃣ Build ranking feature matrix
        # -------------------------------------------------
        rows = []
        for c in candidates:
            row = {
                "item_id": c.item_id,
                "num_retrievers": len(c.sources),
            }
            for src, score in c.scores.items():
                row[f"{src}_score"] = score
            rows.append(row)

        # align feature order
        X = [
            [row.get(col, 0.0) for col in self.feature_columns]
            for row in rows
        ]

        scores = self.ranker.predict(np.asarray(X))

        ranked_items = [
            {
                "item_id": row["item_id"],
                "score": float(score),
                # metadata placeholders (can be joined if available)
                "genres": [],
                "franchise": None,
                "release_timestamp": None,
            }
            for row, score in zip(rows, scores)
        ]

        ranked_items.sort(key=lambda x: x["score"], reverse=True)

        # -------------------------------------------------
        # 3️⃣ Re-ranking (diversity + freshness)
        # -------------------------------------------------
        final_items = self.reranker.rerank(ranked_items)

        return final_items[:top_k]
