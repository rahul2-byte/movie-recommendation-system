import pandas as pd
import numpy as np
import joblib
import json
import faiss
from pathlib import Path
from typing import List, Tuple, Dict, Any

from scipy.sparse import csr_matrix
import implicit # The implicit library for ALS

from common.logger import get_logger
from common.types import Query
from common.config import config
from retrieval.inference.base_retriever import BaseRetriever

log = get_logger(__name__)

# --- ALSBuilder (Offline Training Component) ---

class ALSBuilder:
    def __init__(self, ratings_path: Path, output_dir: Path, embedding_dim: int = 64):
        self.ratings_path = ratings_path
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.embedding_dim = embedding_dim # Desired dimension of ALS embeddings

    def _load_ratings_data(self) -> pd.DataFrame:
        """Loads and preprocesses ratings data."""
        log.info(f"ALSBuilder: Loading ratings data from {self.ratings_path}")
        ratings_df = pd.read_parquet(self.ratings_path)
        log.info(f"ALSBuilder: Loaded {len(ratings_df)} ratings.")
        return ratings_df

    def build_and_save(self):
        """Builds ALS model, extracts item embeddings, and saves artifacts."""
        ratings_df = self._load_ratings_data()

        # Create user_id and movie_id mappings to contiguous integers
        unique_users = ratings_df['userId'].unique()
        unique_movies = ratings_df['movieId'].unique()

        user_to_idx = {user: i for i, user in enumerate(unique_users)}
        movie_to_idx = {int(movie): i for i, movie in enumerate(unique_movies)}
        
        # Save movie_id to index mapping
        with open(Path(config.system.retrieval_artifacts.als.id_map_path), 'w') as f:
            json.dump(movie_to_idx, f)
        log.info(f"ALSBuilder: Saved movie ID to index map to {config.system.retrieval_artifacts.als.id_map_path}")

        # Create sparse user-item matrix for implicit library
        # implicit expects CSR matrix (users x items)
        # However, ALS model in implicit.als.AlternatingLeastSquares learns item_factors
        # based on item_users matrix, which is (items x users)
        
        # Filter for positive interactions (implicit feedback)
        # Use rating >= 3.5 as positive implicit feedback, or just presence of interaction
        positive_ratings = ratings_df[ratings_df['rating'] >= 3.5]
        
        num_users = len(unique_users)
        num_movies = len(unique_movies)

        log.info(f"ALSBuilder: Creating sparse user-item matrix ({num_users} users, {num_movies} movies)...")
        # Build Item-User matrix (items as rows, users as columns)
        # This is the format the implicit library often prefers for item factors
        item_user_data = np.ones(len(positive_ratings)) # Implicit feedback
        item_user_rows = positive_ratings['movieId'].map(movie_to_idx).values
        item_user_cols = positive_ratings['userId'].map(user_to_idx).values

        item_user_matrix = csr_matrix((item_user_data, (item_user_rows, item_user_cols)), 
                                      shape=(num_movies, num_users))
        log.info(f"ALSBuilder: Item-User matrix shape: {item_user_matrix.shape}")

        # --- Train ALS Model ---
        log.info("ALSBuilder: Training ALS model...")
        model = implicit.als.AlternatingLeastSquares(
            factors=self.embedding_dim,
            regularization=0.01,
            iterations=20,
            calculate_training_loss=True,
            random_state=42
        )
        model.fit(item_user_matrix)
        
        # Extract item embeddings
        item_embeddings = model.item_factors
        log.info(f"ALSBuilder: Extracted item embeddings shape: {item_embeddings.shape}")
        
        # --- Build FAISS Index ---
        log.info("ALSBuilder: Building FAISS index...")
        
        # Normalize vectors for cosine similarity (FAISS L2 on normalized vectors)
        faiss_vectors = item_embeddings / np.linalg.norm(item_embeddings, axis=1, keepdims=True)
        faiss_vectors[np.isnan(faiss_vectors)] = 0 # Handle potential NaN from zero-norm vectors
        
        index = faiss.IndexFlatL2(faiss_vectors.shape[1]) # L2 distance
        index.add(faiss_vectors)
        
        # Save FAISS index
        faiss.write_index(index, str(Path(config.system.retrieval_artifacts.als.faiss_index_path)))
        log.info(f"ALSBuilder: Saved FAISS index to {config.system.retrieval_artifacts.als.faiss_index_path}")
        
        # Save item embeddings
        np.save(Path(config.system.retrieval_artifacts.als.embeddings_path), item_embeddings)
        log.info(f"ALSBuilder: Saved item embeddings to {config.system.retrieval_artifacts.als.embeddings_path}")
        
        log.info("ALSBuilder: Building and saving complete.")


# --- ALSRetriever (Online Inference Component) ---

class ALSRetriever(BaseRetriever):
    def __init__(self):
        super().__init__("als")
        self.item_embeddings: np.ndarray = None
        self.index: faiss.Index = None
        self.movie_id_to_idx: Dict[int, int] = None
        self.idx_to_movie_id: Dict[int, int] = None
        self._load_artifacts()
        
    def _load_artifacts(self):
        """Loads the pre-computed ALS item embeddings and FAISS index."""
        from common.model_loader import ensure_local_path
        
        embeddings_path = ensure_local_path(config.system.retrieval_artifacts.als.embeddings_path)
        faiss_path = ensure_local_path(config.system.retrieval_artifacts.als.faiss_index_path)
        id_map_path = ensure_local_path(config.system.retrieval_artifacts.als.id_map_path)

        log.info(f"ALSRetriever: Loading item embeddings from {embeddings_path}")
        self.item_embeddings = np.load(embeddings_path)
        
        log.info(f"ALSRetriever: Loading FAISS index from {faiss_path}")
        self.index = faiss.read_index(str(faiss_path))
        
        log.info(f"ALSRetriever: Loading movie ID map from {id_map_path}")
        with open(id_map_path, 'r') as f:
            self.movie_id_to_idx = {int(k): v for k, v in json.load(f).items()}
        self.idx_to_movie_id = {v: k for k, v in self.movie_id_to_idx.items()}
        
        log.info("ALSRetriever: Artifacts loaded successfully.")

    async def retrieve(self, query: Query, top_k: int = 100) -> List[Tuple[int, float, str]]:
        """
        Retrieves candidates using ALS item-item embeddings via FAISS.
        """
        seed_movie_ids = query.seed_movie_ids
        
        # 1. Get query embedding (average of seed movie embeddings)
        query_embeddings = []
        for mid in seed_movie_ids:
            if mid in self.movie_id_to_idx:
                query_embeddings.append(self.item_embeddings[self.movie_id_to_idx[mid]])
            else:
                log.warning(f"ALSRetriever: Seed movie ID {mid} not found in map. Skipping.")

        if not query_embeddings:
            return []

        query_vector = np.mean(query_embeddings, axis=0).reshape(1, -1).astype(np.float32)
        
        # Normalize query vector for cosine similarity
        norm = np.linalg.norm(query_vector, axis=1, keepdims=True)
        query_vector = np.divide(query_vector, norm, out=np.zeros_like(query_vector), where=norm!=0)
        
        # 2. Perform FAISS search (IndexFlatIP returns Inner Product, which is Cosine Similarity)
        D, I = self.index.search(query_vector, top_k * 2)
        
        candidates_with_scores = []
        for similarity, idx in zip(D[0], I[0]):
            movie_id = self.idx_to_movie_id.get(idx)
            if movie_id is not None and movie_id not in seed_movie_ids:
                candidates_with_scores.append((movie_id, float(similarity), self.name))
            if len(candidates_with_scores) >= top_k:
                break
        
        log.info(f"ALSRetriever: Retrieved {len(candidates_with_scores)} candidates.")
        return candidates_with_scores
