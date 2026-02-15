import json
import logging
from typing import Dict, List, Tuple
import faiss
import numpy as np

from common.config import config
from common.storage.repositories import S3ArtifactRepository
from common.types import Query
from retrieval.inference.base_retriever import BaseRetriever

log = logging.getLogger(__name__)

# --- TFIDF Builder Removed (Was File-Based) ---
# To re-enable training, implement a DynamoDB-based Builder.

# --- TfidfRetriever (Online Inference Component) ---

class TfidfRetriever(BaseRetriever):
    def __init__(self):
        super().__init__("tfidf")
        self.item_embeddings: np.ndarray = None
        self.index: faiss.Index = None
        self.movie_id_to_idx: Dict[int, int] = None
        self.idx_to_movie_id: Dict[int, int] = None
        
        # Initialize S3 Repository
        self.s3_repo = S3ArtifactRepository()
        self._load_artifacts()

    def _load_artifacts(self):
        """Loads artifacts from S3 via Repository."""
        try:
            # 1. Load Embeddings
            emb_key = config.system.model_registry.retrieval.tfidf.embeddings_key
            emb_path = self.s3_repo.download_artifact(emb_key)
            log.info(f"TfidfRetriever: Loading item embeddings from {emb_path}")
            self.item_embeddings = np.load(emb_path)

            # 2. Load FAISS Index
            faiss_key = config.system.model_registry.retrieval.tfidf.faiss_index_key
            faiss_path = self.s3_repo.download_artifact(faiss_key)
            log.info(f"TfidfRetriever: Loading FAISS index from {faiss_path}")
            self.index = faiss.read_index(str(faiss_path))

            # 3. Load ID Map
            map_key = config.system.model_registry.retrieval.tfidf.id_map_key
            self.movie_id_to_idx = self.s3_repo.load_json_artifact(map_key)
            # Ensure keys are ints (JSON keys are strings)
            self.movie_id_to_idx = {int(k): v for k, v in self.movie_id_to_idx.items()}
            self.idx_to_movie_id = {v: k for k, v in self.movie_id_to_idx.items()}

            log.info("TfidfRetriever: Artifacts loaded successfully.")
            
        except Exception as e:
            log.error(f"Failed to load TF-IDF artifacts: {e}")
            # Initialize empty structures to prevent crash
            self.item_embeddings = np.array([])
            self.movie_id_to_idx = {}
            self.idx_to_movie_id = {}
            self.index = None

    async def retrieve(
        self, query: Query, top_k: int = 100
    ) -> List[Tuple[int, float, str]]:
        """
        Retrieves candidates using dense TF-IDF embeddings via FAISS.
        """
        if self.item_embeddings is None or self.index is None:
            return []
            
        seed_movie_ids = query.seed_movie_ids

        # 1. Get query embedding (average of seed movie embeddings)
        query_embeddings = []
        for mid in seed_movie_ids:
            if mid in self.movie_id_to_idx:
                query_embeddings.append(self.item_embeddings[self.movie_id_to_idx[mid]])
            else:
                log.warning(
                    f"TfidfRetriever: Seed movie ID {mid} not found in map. Skipping."
                )

        if not query_embeddings:
            return []

        query_vector = (
            np.mean(query_embeddings, axis=0).reshape(1, -1).astype(np.float32)
        )

        # Normalize query vector for cosine similarity
        norm = np.linalg.norm(query_vector, axis=1, keepdims=True)
        query_vector = np.divide(
            query_vector, norm, out=np.zeros_like(query_vector), where=norm != 0
        )

        # 2. Perform FAISS search (IndexFlatIP returns Inner Product, which is Cosine Similarity)
        # Handle case where index size < top_k
        k = min(top_k * 2, self.index.ntotal)
        if k == 0:
            return []
            
        D, I = self.index.search(query_vector, k)

        candidates_with_scores = []
        for similarity, idx in zip(D[0], I[0]):
            movie_id = self.idx_to_movie_id.get(idx)
            if movie_id is not None and movie_id not in seed_movie_ids:
                candidates_with_scores.append((movie_id, float(similarity), self.name))
            if len(candidates_with_scores) >= top_k:
                break

        log.info(f"TfidfRetriever: Retrieved {len(candidates_with_scores)} candidates.")
        return candidates_with_scores
