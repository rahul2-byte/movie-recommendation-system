import asyncio
from typing import Any, Dict, List

import pandas as pd
from common.logger import get_logger
from common.services.movie_store import MovieStore
from common.types import Candidate, Query
from features.builder import FeatureBuilder
from ranking.inference.lgbm import LGBMRanker
from retrieval.inference.recall import RecallService

log = get_logger(__name__)


class RecommendationPipeline:
    def __init__(
        self,
        recall_service: RecallService,
        feature_builder: FeatureBuilder,
        ranker: LGBMRanker,
        movie_store: MovieStore,
    ):
        self.recall_service = recall_service
        self.feature_builder = feature_builder
        self.ranker = ranker
        self.movie_store = movie_store

    async def recommend(self, query: Query, top_n: int = 20) -> List[Dict[str, Any]]:
        """
        Full recommendation pipeline: Recall -> Feature Engineering -> Ranking -> Enrichment.
        """
        log.info(f"Pipeline: Starting recommendation for seeds: {query.seed_movie_ids}")

        # 1. Recall: Get candidates from multiple sources
        candidates = await self.recall_service.recall(query, top_k=500)
        if not candidates:
            log.warning("Pipeline: No candidates retrieved.")
            return []

        # 2. Feature Engineering: Prepare data for the ranker
        log.info(f"Pipeline: Building features for {len(candidates)} candidates...")
        # Create a temporary DataFrame for the FeatureBuilder
        # All candidates share the same query_movie_ids
        features_input_df = pd.DataFrame(
            {
                "query_movie_ids": [query.seed_movie_ids] * len(candidates),
                "candidate_movie_id": [c.movie_id for c in candidates],
            }
        )

        # FeatureBuilder calculates overlaps and stats
        features_df = self.feature_builder.build_features(features_input_df)

        # 3. Ranking: Score candidates using LightGBM
        ranked_candidates = self.ranker.rank(
            candidates=candidates,
            features_df=features_df,
            limit=top_n * 2,  # Retrieve more for post-processing/filtering
        )

        # 4. Reranking / Post-processing (Optional placeholder)
        # e.g., Diversity filtering, business rules
        final_candidates = ranked_candidates[:top_n]

        # 5. Enrichment: Get full movie metadata from the store in parallel
        log.info(
            f"Pipeline: Enriching {len(final_candidates)} final recommendations in parallel..."
        )

        # Create tasks for all candidates to be enriched concurrently
        enrichment_tasks = [self.movie_store.get(c.movie_id) for c in final_candidates]

        # Wait for all tasks to complete
        movie_metas = await asyncio.gather(*enrichment_tasks)

        enriched_results = []
        for c, movie_meta in zip(final_candidates, movie_metas):
            if movie_meta:
                # Add scores for transparency in UI if needed
                result = movie_meta.copy()
                result["score"] = c.rank_score
                result["retrieval_sources"] = c.sources
                enriched_results.append(result)

        log.info(f"Pipeline: Returning {len(enriched_results)} results.")
        return enriched_results
