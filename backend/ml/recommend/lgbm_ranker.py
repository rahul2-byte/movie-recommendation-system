from typing import List
import numpy as np
import lightgbm as lgb
import hashlib

from api.recommend.types import Candidate
from api.recommend.model_registry import get_lgbm_model


class LGBMRanker:
    """
    LightGBM LambdaRank based ranker.
    Feature schema MUST match training exactly.
    """

    FEATURE_NAMES = [
        "query_id",
        "retrieved_by_two_tower",
        "retrieved_by_als",
        "retrieved_by_item_cf",
        "retrieved_by_content",
        "two_tower_score",
        "als_score",
        "item_cf_score",
        "content_score",
        "num_retrievers",
    ]

    def __init__(self, model_path: str):
        self.model = get_lgbm_model(model_path)

        if self.model.num_feature() != len(self.FEATURE_NAMES):
            raise RuntimeError(
                f"Model expects {self.model.num_feature()} features, "
                f"but {len(self.FEATURE_NAMES)} were provided"
            )

    # ---------------------------------------------------------
    # Query ID handling (CRITICAL)
    # ---------------------------------------------------------
    @staticmethod
    def _make_query_id(seed_movie_ids: List[int]) -> float:
        """
        Convert list of seed movies into a stable numeric query_id.
        MUST be deterministic.
        """
        key = "_".join(map(str, sorted(seed_movie_ids)))
        digest = hashlib.md5(key.encode()).hexdigest()
        return float(int(digest[:8], 16))  # safe numeric id

    # ---------------------------------------------------------
    # Feature construction
    # ---------------------------------------------------------
    def _build_feature_row(
        self,
        candidate: Candidate,
        query_id: float,
    ) -> List[float]:

        sources = set(candidate.sources)
        scores = candidate.scores

        return [
            query_id,
            float("two_tower" in sources),
            float("als" in sources),
            float("item_cf" in sources),
            float("content" in sources),
            float(scores.get("two_tower", 0.0)),
            float(scores.get("als", 0.0)),
            float(scores.get("item_cf", 0.0)),
            float(scores.get("content", 0.0)),
            float(len(sources)),
        ]

    # ---------------------------------------------------------
    # Ranking
    # ---------------------------------------------------------
    def rank(
        self,
        candidates: List[Candidate],
        seed_movie_ids: List[int],
        limit: int = 20,
    ) -> List[Candidate]:

        if not candidates:
            return []

        query_id = self._make_query_id(seed_movie_ids)

        X = np.array(
            [self._build_feature_row(c, query_id) for c in candidates],
            dtype=np.float32,
        )

        if X.shape[1] != self.model.num_feature():
            raise RuntimeError(
                f"Feature mismatch: {X.shape[1]} vs {self.model.num_feature()}"
            )

        scores = self.model.predict(X)

        for c, s in zip(candidates, scores):
            c.rank_score = float(s)

        return sorted(candidates, key=lambda c: c.rank_score, reverse=True)[:limit]
