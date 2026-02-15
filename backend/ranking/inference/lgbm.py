from typing import List
import lightgbm as lgb
import numpy as np
import pandas as pd
from common.logger import get_logger
from common.types import Candidate
from common.config import config
from common.storage.repositories import S3ArtifactRepository

log = get_logger(__name__)

class LGBMRanker:
    """
    LightGBM LambdaRank based ranker.
    Feature schema MUST match training exactly.
    """

    def __init__(self):
        # Initialize S3 Repository
        self.s3_repo = S3ArtifactRepository()
        
        # Download Model
        model_key = config.system.model_registry.ranker.model_key
        model_path = self.s3_repo.download_artifact(model_key)
        
        # Load Model
        self.model = lgb.Booster(model_file=str(model_path))
        self.feature_names = config.features.ranker_features
        
        log.info(
            f"LGBMRanker: Loaded model from {model_path} with {self.model.num_feature()} features."
        )
        log.info(f"LGBMRanker: Using features: {self.feature_names}")

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
            log.warning(
                "ranker.skip empty_input candidates=%s features_empty=%s",
                len(candidates) if candidates else 0,
                features_df.empty if hasattr(features_df, "empty") else True,
            )
            return candidates

        # Ensure features are in the correct order
        # Fallback if config is missing keys (though it shouldn't be)
        if not self.feature_names:
            log.warning(
                "LGBMRanker: Feature names not found in config, using all 'feat_' columns."
            )
            self.feature_names = [
                c for c in features_df.columns if c.startswith("feat_")
            ]

        # Check for missing columns and fill with 0
        for col in self.feature_names:
            if col not in features_df.columns:
                log.warning(f"LGBMRanker: Missing feature {col}, filling with 0.")
                features_df[col] = 0.0

        X = features_df[self.feature_names].values.astype(np.float32)

        if X.shape[1] != self.model.num_feature():
            # Try to degrade gracefully if model is older/newer
            log.error(
                f"LGBMRanker: Feature mismatch. Model expects {self.model.num_feature()}, "
                f"but got {X.shape[1]}. Features used: {self.feature_names}"
            )
            return candidates[:limit]

        # Predict relevance scores
        scores = self.model.predict(X)

        # Attach scores to candidates
        # We assume the order in features_df matches the order of candidates
        for c, s in zip(candidates, scores):
            c.rank_score = float(s)

        # Sort by rank_score descending
        ranked_candidates = sorted(candidates, key=lambda c: c.rank_score, reverse=True)

        log.info(
            "ranker.success input_candidates=%s output_candidates=%s feature_cols=%s",
            len(candidates),
            len(ranked_candidates[:limit]),
            X.shape[1],
        )
        return ranked_candidates[:limit]
