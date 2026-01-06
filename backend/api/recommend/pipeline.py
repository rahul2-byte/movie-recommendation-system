from api.recommend.recall_service import RecallService
from api.recommend.lgbm_ranker import LGBMRanker
from api.services.movie_store import MovieStore
from pathlib import Path


class RecommendationPipeline:
    def __init__(self):
        self.recall_service = RecallService()
        self.ranker = LGBMRanker(model_path="./backend/models/ranker/lgbm_lambdarank.txt")
        self.movie_store = MovieStore(Path("./backend/data/raw/movies.csv"), Path("./backend/data/raw/links.csv"))

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
