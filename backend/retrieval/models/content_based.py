import logging
import pickle

import faiss
import numpy as np
from common.config import config
from common.storage.repositories import S3ArtifactRepository
from common.types import Query

from retrieval.inference.base_retriever import BaseRetriever

log = logging.getLogger(__name__)


class ContentBasedRetriever(BaseRetriever):
    def __init__(self):
        super().__init__("content_based")
        self.item_embeddings: np.ndarray = None
        self.index: faiss.Index = None
        self.tmdb_id_to_idx: dict[int, int] = None
        self.idx_to_tmdb_id: dict[int, int] = None
        self.preprocessors: dict = None

        self.s3_repo = S3ArtifactRepository()
        self._load_artifacts()

    def _load_artifacts(self):
        try:
            reg = config.system.model_registry.retrieval.content_based

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

            # Optional preprocessors are not required for current retrieval logic.
            if hasattr(reg, "preprocessors_key"):
                try:
                    prep_path = self.s3_repo.download_artifact(reg.preprocessors_key)
                    with open(prep_path, "rb") as f:
                        self.preprocessors = pickle.load(f)
                except Exception as e:
                    log.warning(
                        "ContentBasedRetriever: Optional preprocessors missing (%s). Continuing without them.",
                        e,
                    )

            log.info("ContentBasedRetriever: Artifacts loaded.")

        except Exception as e:
            log.error(f"Failed to load ContentBased artifacts: {e}")
            self.index = None

    async def retrieve(
        self, query: Query, top_k: int = 100
    ) -> list[tuple[int, float, str]]:
        if self.index is None:
            return []

        seed_tmdb_ids = query.seed_tmdb_ids
        query_embeddings = []
        for tmdb_id in seed_tmdb_ids:
            if tmdb_id in self.tmdb_id_to_idx:
                query_embeddings.append(
                    self.item_embeddings[self.tmdb_id_to_idx[tmdb_id]]
                )

        if not query_embeddings:
            return []

        query_vector = (
            np.mean(query_embeddings, axis=0).reshape(1, -1).astype(np.float32)
        )
        norm = np.linalg.norm(query_vector, axis=1, keepdims=True)
        query_vector = np.divide(
            query_vector, norm, out=np.zeros_like(query_vector), where=norm != 0
        )

        k = min(top_k * 2, self.index.ntotal)
        distances, indices = self.index.search(query_vector, k)

        candidates = []
        for sim, idx in zip(distances[0], indices[0], strict=True):
            tmdb_id = self.idx_to_tmdb_id.get(idx)
            if tmdb_id and tmdb_id not in seed_tmdb_ids:
                candidates.append((tmdb_id, float(sim), self.name))
            if len(candidates) >= top_k:
                break

        return candidates
