import json
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

import faiss
import joblib
import numpy as np
import pandas as pd
from common.config import config
from common.logger import get_logger
from common.types import Query
from scipy.sparse import csr_matrix, load_npz, save_npz
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from retrieval.inference.base_retriever import BaseRetriever

log = get_logger(__name__)

# --- TFIDF Builder (Offline Training Component) ---


class TFIDFBuilder:
    def __init__(self, movies_metadata_path: Path, output_dir: Path):
        self.movies_metadata_path = movies_metadata_path
        self.output_dir = output_dir
        self.output_dir.mkdir(
            parents=True, exist_ok=True
        )  # Ensure output directory exists

    def _load_movies_metadata(self) -> pd.DataFrame:
        """Loads and preprocesses movie metadata."""
        log.info(
            f"TFIDFBuilder: Loading movie metadata from {self.movies_metadata_path}"
        )
        movies_df = pd.read_parquet(self.movies_metadata_path)

        # Ensure 'genres' column is in expected format (list of strings or string)
        movies_df["genres"] = movies_df["genres"].apply(self._ensure_list_of_strings)

        # Combine genres into a single string for TF-IDF
        movies_df["genres_str"] = movies_df["genres"].apply(
            lambda g: " ".join(g) if isinstance(g, list) and g else ""
        )
        log.info(f"TFIDFBuilder: Loaded {len(movies_df)} movies.")
        return movies_df

    def _ensure_list_of_strings(self, item: Any) -> List[str]:
        """Ensures an item is a list of strings, converting if necessary."""
        if item is None:
            return []
        if isinstance(item, list):
            return [str(x) for x in item]
        if isinstance(item, str):
            try:  # Attempt to convert string representation of list to actual list
                evaluated = json.loads(item)
                if isinstance(evaluated, list):
                    return [str(x) for x in evaluated]
            except json.JSONDecodeError:
                pass
        return [
            str(item)
        ]  # Default to a list containing the string representation of the item

    def build_and_save(self):
        """Builds the TF-IDF model and saves all artifacts."""
        movies_df = self._load_movies_metadata()

        # Create movie_id to index mapping
        movie_id_to_idx = {
            movie_id: idx for idx, movie_id in enumerate(movies_df["movie_id"])
        }
        with open(Path(config.system.retrieval_artifacts.tfidf.id_map_path), "w") as f:
            json.dump(movie_id_to_idx, f)
        log.info(
            f"TFIDFBuilder: Saved movie ID to index map to {config.system.retrieval_artifacts.tfidf.id_map_path}"
        )

        # Fit TF-IDF vectorizer
        log.info("TFIDFBuilder: Fitting TfidfVectorizer...")
        self.vectorizer = TfidfVectorizer(min_df=5, max_df=0.9)  # Tunable parameters
        tfidf_matrix = self.vectorizer.fit_transform(movies_df["genres_str"])
        log.info(f"TFIDFBuilder: TF-IDF matrix shape: {tfidf_matrix.shape}")

        # Save vectorizer and TF-IDF matrix
        joblib.dump(
            self.vectorizer,
            Path(config.system.retrieval_artifacts.tfidf.vectorizer_path),
        )
        log.info(
            f"TFIDFBuilder: Saved TfidfVectorizer to {config.system.retrieval_artifacts.tfidf.vectorizer_path}"
        )

        save_npz(
            Path(config.system.retrieval_artifacts.tfidf.matrix_path), tfidf_matrix
        )
        log.info(
            f"TFIDFBuilder: Saved TF-IDF matrix to {config.system.retrieval_artifacts.tfidf.matrix_path}"
        )
        log.info("TFIDFBuilder: Building and saving complete.")


# --- TfidfRetriever (Online Inference Component) ---


class TfidfRetriever(BaseRetriever):
    def __init__(self):
        super().__init__("tfidf")
        self.item_embeddings: np.ndarray = None
        self.index: faiss.Index = None
        self.movie_id_to_idx: Dict[int, int] = None
        self.idx_to_movie_id: Dict[int, int] = None
        self._load_artifacts()

    def _load_artifacts(self):
        """Loads the pre-computed TF-IDF embeddings and FAISS index."""
        from common.model_loader import ensure_local_path

        embeddings_path = ensure_local_path(
            config.system.retrieval_artifacts.tfidf.embeddings_path
        )
        faiss_path = ensure_local_path(
            config.system.retrieval_artifacts.tfidf.faiss_index_path
        )
        id_map_path = ensure_local_path(
            config.system.retrieval_artifacts.tfidf.id_map_path
        )

        log.info(f"TfidfRetriever: Loading item embeddings from {embeddings_path}")
        self.item_embeddings = np.load(embeddings_path)

        log.info(f"TfidfRetriever: Loading FAISS index from {faiss_path}")
        self.index = faiss.read_index(str(faiss_path))

        log.info(f"TfidfRetriever: Loading movie ID map from {id_map_path}")
        with open(id_map_path, "r") as f:
            self.movie_id_to_idx = {int(k): v for k, v in json.load(f).items()}
        self.idx_to_movie_id = {v: k for k, v in self.movie_id_to_idx.items()}

        log.info("TfidfRetriever: Artifacts loaded successfully.")

    async def retrieve(
        self, query: Query, top_k: int = 100
    ) -> List[Tuple[int, float, str]]:
        """
        Retrieves candidates using dense TF-IDF embeddings via FAISS.
        """
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
        D, I = self.index.search(query_vector, top_k * 2)

        candidates_with_scores = []
        for similarity, idx in zip(D[0], I[0]):
            movie_id = self.idx_to_movie_id.get(idx)
            if movie_id is not None and movie_id not in seed_movie_ids:
                candidates_with_scores.append((movie_id, float(similarity), self.name))
            if len(candidates_with_scores) >= top_k:
                break

        log.info(f"TfidfRetriever: Retrieved {len(candidates_with_scores)} candidates.")
        return candidates_with_scores
