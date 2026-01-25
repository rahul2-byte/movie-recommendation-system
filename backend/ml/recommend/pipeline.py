from backend.ml.recommend.recall_service import RecallService
from backend.ml.recommend.lgbm_ranker import LGBMRanker
from backend.services.movie_store import MovieStore


class RecommendationPipeline:
    def __init__(
        self,
        recall_service: RecallService,
        ranker: LGBMRanker,
        movie_store: MovieStore,
    ):
        self.recall_service = recall_service
        self.ranker = ranker
        self.movie_store = movie_store

    def run(self, seed_movie_ids, moods, limit):

        candidates = self.recall_service.recall(seed_movie_ids)

        ranked = self.ranker.rank(
            candidates=candidates,
            seed_movie_ids=seed_movie_ids,
            limit=limit,
        )

        enriched = []
        for c in ranked:
            meta = self.movie_store.get(c.item_id)
            if not meta:
                continue
            enriched.append(meta)

        return enriched
