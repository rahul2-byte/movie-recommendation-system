from typing import List
import numpy as np
import pandas as pd
import lightgbm as lgb
from common.types import Candidate
from common.model_loader import get_lgbm_model
from common.logger import get_logger

log = get_logger(__name__)

class LGBMRanker:
    """
    LightGBM LambdaRank based ranker.
    Feature schema MUST match training exactly:
    1. feat_avg_query_rating
    2. feat_genre_overlap
    3. feat_candidate_avg_rating
    4. feat_candidate_rating_count
    """

    FEATURE_NAMES = [
        "feat_avg_query_rating",
        "feat_genre_overlap",
        "feat_candidate_avg_rating",
        "feat_candidate_rating_count",
    ]

    def __init__(self, model_path: str):
        self.model = get_lgbm_model(model_path)
        log.info(f"LGBMRanker: Loaded model from {model_path} with {self.model.num_feature()} features.")

    def rank(
        self,
        candidates: List[Candidate],
        features_df: pd.DataFrame,
        limit: int = 100,
    ) -> List[Candidate]:
        """
        Ranks candidates using the provided features.
        """
        if not candidates or features_df.empty:
            return candidates

        # Ensure features are in the correct order
        X = features_df[self.FEATURE_NAMES].values.astype(np.float32)

        if X.shape[1] != self.model.num_feature():
            raise RuntimeError(
                f"LGBMRanker: Feature mismatch. Model expects {self.model.num_feature()}, "
                f"but got {X.shape[1]}"
            )

        # Predict relevance scores
        scores = self.model.predict(X)

        # Attach scores to candidates
        # We assume the order in features_df matches the order of candidates
        for c, s in zip(candidates, scores):
            c.rank_score = float(s)

        # Sort by rank_score descending
        ranked_candidates = sorted(candidates, key=lambda c: c.rank_score, reverse=True)
        
        log.info(f"LGBMRanker: Ranked {len(ranked_candidates)} candidates.")
        return ranked_candidates[:limit]
