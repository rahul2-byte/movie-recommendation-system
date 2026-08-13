import logging
from collections import defaultdict

import faiss
import numpy as np
from common.config import config
from common.storage.repositories import S3ArtifactRepository
from common.types import Query

from retrieval.inference.base_retriever import BaseRetriever
from retrieval.seeded import collect_seed_candidates, order_candidate_ids

log = logging.getLogger(__name__)


class TwoTowerRetriever(BaseRetriever):
    def __init__(self):
        super().__init__("two_tower")
        self.item_embeddings: np.ndarray = None
        self.index: faiss.Index = None
        self.tmdb_id_to_idx: dict[int, int] = None
        self.idx_to_tmdb_id: dict[int, int] = None
        self.s3_repo = S3ArtifactRepository()
        self._load_artifacts()

    def _load_artifacts(self):
        try:
            reg = config.system.model_registry.retrieval.two_tower

            # Embeddings
            emb_path = self.s3_repo.download_artifact(reg.embeddings_key)
            self.item_embeddings = np.load(emb_path)

            # FAISS
            faiss_path = self.s3_repo.download_artifact(reg.faiss_index_key)
            self.index = faiss.read_index(str(faiss_path))

            # ID Map
            self.tmdb_id_to_idx = self.s3_repo.load_json_artifact(reg.id_map_key)
            self.tmdb_id_to_idx = {int(k): v for k, v in self.tmdb_id_to_idx.items()}
            self.idx_to_tmdb_id = {v: k for k, v in self.tmdb_id_to_idx.items()}

            log.info("TwoTowerRetriever: Artifacts loaded.")

        except Exception as e:
            log.error(f"Failed to load TwoTower artifacts: {e}")
            self.index = None

    async def retrieve(
        self, query: Query, top_k: int = 100
    ) -> list[tuple[int, float, str]]:
        if self.index is None:
            return []

        per_seed_candidates = max(top_k, 200)

        def retrieve_one(seed_tmdb_id: int, count: int):
            position = self.tmdb_id_to_idx.get(seed_tmdb_id)
            if position is None:
                return []
            scores, indices = self.index.search(
                self.item_embeddings[position : position + 1],
                min(self.index.ntotal, count + 1),
            )
            return [
                (self.idx_to_tmdb_id[int(index)], float(score))
                for score, index in zip(scores[0], indices[0], strict=True)
                if int(index) >= 0
            ]

        evidence = collect_seed_candidates(
            query.seed_tmdb_ids,
            retrieve_one=retrieve_one,
            source=self.name,
            top_k=per_seed_candidates,
        )
        scores_by_movie = defaultdict(list)
        for row in evidence:
            scores_by_movie[row.candidate_tmdb_id].append(row.score)
        return [
            (movie_id, max(scores_by_movie[movie_id]), self.name)
            for movie_id in order_candidate_ids(evidence)[:top_k]
        ]
