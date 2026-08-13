import time
from typing import Any

from common.logger import get_logger
from common.services.movie_store import MovieStore
from common.types import Query
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

    async def recommend(
        self, query: Query, top_n: int = 20, request_id: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Full recommendation pipeline: Recall -> Metadata Fetch -> Feature Engineering -> Ranking.
        """
        req = request_id or "n/a"
        t0 = time.perf_counter()
        log.info(
            "pipeline.start request_id={} seed_count={} top_n={} seeds={}",
            req,
            len(query.seed_tmdb_ids),
            top_n,
            query.seed_tmdb_ids,
        )

        # 0. Fetch Seed Metadata (Batch from DB)
        try:
            s0 = time.perf_counter()
            seeds_meta = await self.movie_store.get_many_by_tmdb_ids(
                query.seed_tmdb_ids
            )
            log.info(
                "pipeline.step.seed_fetch request_id={} requested={} found={} duration_ms={}",
                req,
                len(query.seed_tmdb_ids),
                len(seeds_meta),
                int((time.perf_counter() - s0) * 1000),
            )
            if not seeds_meta:
                log.warning(
                    "pipeline.no_seeds_found request_id={} seeds={}",
                    req,
                    query.seed_tmdb_ids,
                )
                return []
        except Exception:
            log.exception(
                "pipeline.seed_fetch_failed request_id={} seeds={}",
                req,
                query.seed_tmdb_ids,
            )
            raise

        # 1. Recall: Get candidates from multiple sources
        try:
            s1 = time.perf_counter()
            candidates = await self.recall_service.recall(
                query, top_k=500, request_id=req
            )
            log.info(
                "pipeline.step.recall request_id={} candidates={} duration_ms={}",
                req,
                len(candidates),
                int((time.perf_counter() - s1) * 1000),
            )
            if not candidates:
                log.warning("pipeline.no_candidates request_id={}", req)
                return []
        except Exception:
            log.exception("pipeline.recall_failed request_id={}", req)
            raise

        # 2. Fetch Candidate Metadata (Batch from DB)
        try:
            s2 = time.perf_counter()
            candidate_ids = [c.tmdb_id for c in candidates]
            candidates_meta_list = await self.movie_store.get_many_by_tmdb_ids(
                candidate_ids
            )
            meta_map = {m["tmdbId"]: m for m in candidates_meta_list}

            valid_candidates = []
            valid_meta = []
            for c in candidates:
                if c.tmdb_id in meta_map:
                    valid_candidates.append(c)
                    valid_meta.append(meta_map[c.tmdb_id])

            log.info(
                "pipeline.step.candidate_meta request_id={} requested={} fetched={} valid={} duration_ms={}",
                req,
                len(candidate_ids),
                len(candidates_meta_list),
                len(valid_candidates),
                int((time.perf_counter() - s2) * 1000),
            )

            if not valid_candidates:
                log.warning("pipeline.no_valid_candidates request_id={}", req)
                return []
        except Exception:
            log.exception("pipeline.candidate_meta_failed request_id={}", req)
            raise

        # 3. Feature Engineering: Build features on-the-fly
        try:
            s3 = time.perf_counter()
            features_df = self.feature_builder.build_features(seeds_meta, valid_meta)
            log.info(
                "pipeline.step.features request_id={} rows={} cols={} duration_ms={}",
                req,
                len(features_df.index) if hasattr(features_df, "index") else 0,
                len(features_df.columns) if hasattr(features_df, "columns") else 0,
                int((time.perf_counter() - s3) * 1000),
            )
        except Exception:
            log.exception("pipeline.feature_build_failed request_id={}", req)
            raise

        # 4. Ranking: Score candidates using LightGBM
        try:
            s4 = time.perf_counter()
            ranked_candidates = self.ranker.rank(
                candidates=valid_candidates,
                features_df=features_df,
                limit=top_n * 2,
            )
            log.info(
                "pipeline.step.rank request_id={} ranked={} duration_ms={}",
                req,
                len(ranked_candidates),
                int((time.perf_counter() - s4) * 1000),
            )
        except Exception:
            log.exception("pipeline.rank_failed request_id={}", req)
            raise

        # 5. Format Response
        # ------------------
        # The candidates are already enriched via 'valid_meta' (conceptually).
        # But 'ranked_candidates' are Candidate objects.
        # We need to join them back with the metadata we already fetched.

        final_results = []
        for c in ranked_candidates[:top_n]:
            # Reuse the metadata we fetched in Step 2!
            # No need to fetch again.
            movie_meta = meta_map.get(c.tmdb_id)
            if movie_meta:
                result = movie_meta.copy()
                result["score"] = c.rank_score
                result["retrieval_sources"] = c.sources
                final_results.append(result)

        log.info(
            "pipeline.success request_id={} results={} total_duration_ms={}",
            req,
            len(final_results),
            int((time.perf_counter() - t0) * 1000),
        )
        return final_results
