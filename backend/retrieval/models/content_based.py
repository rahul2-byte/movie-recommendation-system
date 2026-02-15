import json
import logging
import pickle
from typing import Dict, List, Tuple

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
        self.movie_id_to_idx: Dict[int, int] = None
        self.idx_to_movie_id: Dict[int, int] = None
        self.preprocessors: Dict = None
        
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
            self.movie_id_to_idx = self.s3_repo.load_json_artifact(reg.id_map_key)
            self.movie_id_to_idx = {int(k): v for k, v in self.movie_id_to_idx.items()}
            self.idx_to_movie_id = {v: k for k, v in self.movie_id_to_idx.items()}
            
            # Preprocessors (if needed for inference)
            if hasattr(reg, 'preprocessors_key'):
                prep_path = self.s3_repo.download_artifact(reg.preprocessors_key)
                with open(prep_path, 'rb') as f:
                    self.preprocessors = pickle.load(f)
                    
            log.info("ContentBasedRetriever: Artifacts loaded.")
            
        except Exception as e:
            log.error(f"Failed to load ContentBased artifacts: {e}")
            self.index = None

    async def retrieve(
        self, query: Query, top_k: int = 100
    ) -> List[Tuple[int, float, str]]:
        if self.index is None:
            return []
            
        seed_movie_ids = query.seed_movie_ids
        query_embeddings = []
        for mid in seed_movie_ids:
            if mid in self.movie_id_to_idx:
                query_embeddings.append(self.item_embeddings[self.movie_id_to_idx[mid]])
        
        if not query_embeddings:
            return []
            
        query_vector = np.mean(query_embeddings, axis=0).reshape(1, -1).astype(np.float32)
        norm = np.linalg.norm(query_vector, axis=1, keepdims=True)
        query_vector = np.divide(query_vector, norm, out=np.zeros_like(query_vector), where=norm!=0)
        
        k = min(top_k * 2, self.index.ntotal)
        D, I = self.index.search(query_vector, k)
        
        candidates = []
        for sim, idx in zip(D[0], I[0]):
            mid = self.idx_to_movie_id.get(idx)
            if mid and mid not in seed_movie_ids:
                candidates.append((mid, float(sim), self.name))
            if len(candidates) >= top_k:
                break
                
        return candidates
