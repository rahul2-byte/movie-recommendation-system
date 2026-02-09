import json
import warnings
from pathlib import Path
from typing import Any, Dict, List, Tuple

import faiss
import joblib
import numpy as np
import pandas as pd
from common.config import config
from common.logger import get_logger
from common.types import Query
from configs.settings import TOP_N_TAGS
from scipy.sparse import csr_matrix
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import MultiLabelBinarizer, StandardScaler

from retrieval.inference.base_retriever import BaseRetriever

log = get_logger(__name__)

# --- ContentBasedBuilder (Offline Training Component) ---


class ContentBasedBuilder:
    def __init__(
        self,
        movies_metadata_path: Path,
        tags_path: Path,
        output_dir: Path,
        embedding_dim: int = 64,
    ):
        self.movies_metadata_path = movies_metadata_path
        self.tags_path = tags_path
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.embedding_dim = (
            embedding_dim  # Desired dimension of final content embedding
        )

    def _load_data(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Loads and preprocesses movie and tag data."""
        log.info(
            f"ContentBasedBuilder: Loading movie metadata from {self.movies_metadata_path}"
        )
        movies_df = pd.read_parquet(self.movies_metadata_path)
        log.info(f"ContentBasedBuilder: Loaded {len(movies_df)} movies.")

        log.info(f"ContentBasedBuilder: Loading tags from {self.tags_path}")
        tags_df = pd.read_parquet(self.tags_path)
        log.info(f"ContentBasedBuilder: Loaded {len(tags_df)} tags.")
        return movies_df, tags_df

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
        """Builds content-based embeddings and saves all artifacts."""
        movies_df, tags_df = self._load_data()

        # Ensure movie_id is consistent
        if "movieId" in movies_df.columns:
            movies_df = movies_df.rename(columns={"movieId": "movie_id"})
        movies_df = movies_df.set_index("movie_id")

        # Create movie_id to index mapping
        movie_id_to_idx = {
            movie_id: idx for idx, movie_id in enumerate(movies_df.index)
        }
        with open(
            Path(config.system.retrieval_artifacts.content_based.id_map_path), "w"
        ) as f:
            json.dump(movie_id_to_idx, f)
        log.info(
            f"ContentBasedBuilder: Saved movie ID to index map to {config.system.retrieval_artifacts.content_based.id_map_path}"
        )

        # --- Feature Engineering ---
        log.info("ContentBasedBuilder: Starting feature engineering...")

        # 1. Genres (MultiLabelBinarizer)
        movies_df["genres"] = movies_df["genres"].apply(self._ensure_list_of_strings)
        genre_mlb = MultiLabelBinarizer()
        genre_features = genre_mlb.fit_transform(movies_df["genres"])
        log.info(f"ContentBasedBuilder: Genre features shape: {genre_features.shape}")

        # 2. Tags (MultiLabelBinarizer for top N tags)
        tags_df.dropna(subset=["tag"], inplace=True)
        tags_df["tag"] = tags_df["tag"].str.lower()
        top_tags = tags_df["tag"].value_counts().nlargest(TOP_N_TAGS).index.tolist()
        tag_mlb = MultiLabelBinarizer(classes=top_tags)

        movie_tags = (
            tags_df.groupby("movieId")["tag"]
            .apply(list)
            .reindex(movies_df.index, fill_value=[])
        )
        top_tags_set = set(top_tags)
        # Filter to top tags to avoid noisy warnings and keep features consistent.
        movie_tags = movie_tags.apply(
            lambda tags: [t for t in tags if t in top_tags_set]
        )
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message=r"unknown class\(es\).*will be ignored",
                category=UserWarning,
            )
            tag_features = tag_mlb.fit_transform(movie_tags)  # Returns sparse matrix
        log.info(f"ContentBasedBuilder: Tag features shape: {tag_features.shape}")

        # 3. Numerical Features (StandardScaler)
        for col, default in [
            ("release_year", 0),
            ("vote_average", 0.0),
            ("popularity_score", 0.0),
        ]:
            if col not in movies_df.columns:
                movies_df[col] = default
        numerical_features_df = movies_df[
            ["release_year", "vote_average", "popularity_score"]
        ].fillna(0)
        scaler = StandardScaler()
        numerical_features = scaler.fit_transform(numerical_features_df)
        log.info(
            f"ContentBasedBuilder: Numerical features shape: {numerical_features.shape}"
        )

        # --- Combine Features ---
        # Convert sparse matrices to dense if needed for concatenation with numpy
        genre_features_dense = genre_features
        if hasattr(tag_features, "toarray"):
            tag_features_dense = tag_features.toarray()
        else:
            tag_features_dense = tag_features

        all_features = np.hstack(
            [genre_features_dense, tag_features_dense, numerical_features]
        ).astype(np.float32)

        log.info(f"ContentBasedBuilder: Combined features shape: {all_features.shape}")

        # --- Build FAISS Index ---
        log.info("ContentBasedBuilder: Building FAISS index...")

        # Normalize vectors for cosine similarity (FAISS L2 on normalized vectors)
        faiss_vectors = all_features / np.linalg.norm(
            all_features, axis=1, keepdims=True
        )
        faiss_vectors[np.isnan(faiss_vectors)] = (
            0  # Handle potential NaN from zero-norm vectors
        )

        index = faiss.IndexFlatL2(faiss_vectors.shape[1])  # L2 distance
        index.add(faiss_vectors)

        # Save FAISS index
        faiss.write_index(
            index,
            str(Path(config.system.retrieval_artifacts.content_based.faiss_index_path)),
        )
        log.info(
            f"ContentBasedBuilder: Saved FAISS index to {config.system.retrieval_artifacts.content_based.faiss_index_path}"
        )

        # Save embeddings and preprocessors
        np.save(
            Path(config.system.retrieval_artifacts.content_based.embeddings_path),
            all_features,
        )
        log.info(
            f"ContentBasedBuilder: Saved item embeddings to {config.system.retrieval_artifacts.content_based.embeddings_path}"
        )

        preprocessors = {"genre_mlb": genre_mlb, "tag_mlb": tag_mlb, "scaler": scaler}
        joblib.dump(
            preprocessors,
            Path(config.system.retrieval_artifacts.content_based.preprocessors_path),
        )
        log.info(
            f"ContentBasedBuilder: Saved preprocessors to {config.system.retrieval_artifacts.content_based.preprocessors_path}"
        )

        log.info("ContentBasedBuilder: Building and saving complete.")


# --- ContentBasedRetriever (Online Inference Component) ---


class ContentBasedRetriever(BaseRetriever):
    def __init__(self):
        super().__init__("content_based")
        self.item_embeddings: np.ndarray = None
        self.index: faiss.Index = None
        self.movie_id_to_idx: Dict[int, int] = None
        self.idx_to_movie_id: Dict[int, int] = None
        self._load_artifacts()

    def _load_artifacts(self):
        """Loads the pre-computed content embeddings and FAISS index."""
        from common.model_loader import ensure_local_path

        embeddings_path = ensure_local_path(
            config.system.retrieval_artifacts.content_based.embeddings_path
        )
        faiss_path = ensure_local_path(
            config.system.retrieval_artifacts.content_based.faiss_index_path
        )
        id_map_path = ensure_local_path(
            config.system.retrieval_artifacts.content_based.id_map_path
        )

        log.info(
            f"ContentBasedRetriever: Loading item embeddings from {embeddings_path}"
        )
        self.item_embeddings = np.load(embeddings_path)

        log.info(f"ContentBasedRetriever: Loading FAISS index from {faiss_path}")
        self.index = faiss.read_index(str(faiss_path))

        log.info(f"ContentBasedRetriever: Loading movie ID map from {id_map_path}")
        with open(id_map_path, "r") as f:
            self.movie_id_to_idx = {int(k): v for k, v in json.load(f).items()}
        self.idx_to_movie_id = {v: k for k, v in self.movie_id_to_idx.items()}

        log.info("ContentBasedRetriever: Artifacts loaded successfully.")

    async def retrieve(
        self, query: Query, top_k: int = 100
    ) -> List[Tuple[int, float, str]]:
        """
        Retrieves candidates using content-based embeddings via FAISS.
        """
        seed_movie_ids = query.seed_movie_ids

        # 1. Get query embedding (average of seed movie embeddings)
        query_embeddings = []
        for mid in seed_movie_ids:
            if mid in self.movie_id_to_idx:
                query_embeddings.append(self.item_embeddings[self.movie_id_to_idx[mid]])
            else:
                log.warning(
                    f"ContentBasedRetriever: Seed movie ID {mid} not found in map. Skipping."
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

        log.info(
            f"ContentBasedRetriever: Retrieved {len(candidates_with_scores)} candidates."
        )
        return candidates_with_scores
