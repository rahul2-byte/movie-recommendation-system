# backend/features/builder.py
"""
Builds query-relative features for the ranking model.
This version is heavily optimized to work with pre-vectorized, shared-memory data.
"""
import time
import logging
from typing import List, Dict

import numpy as np
import pandas as pd
from scipy.sparse import spmatrix

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


class FeatureBuilder:
    """
    Constructs query-relative features using pre-calculated, shared-memory matrices for vectors.
    """

    @classmethod
    def from_paths(cls, movies_path: str, tags_path: str):
        """
        Initializes FeatureBuilder by loading and processing data from specified paths.
        """
        from common.model_loader import ensure_local_path
        
        # Ensure local copies in PROD
        local_movies_path = ensure_local_path(movies_path)
        local_tags_path = ensure_local_path(tags_path)
        
        log.info(f"Initializing FeatureBuilder from {local_movies_path} and {local_tags_path}...")
        
        from sklearn.preprocessing import MultiLabelBinarizer
        import scipy.sparse

        movies_df = pd.read_parquet(local_movies_path)
        if "vote_average" not in movies_df.columns: movies_df["vote_average"] = 0.0
        if "vote_count" not in movies_df.columns: movies_df["vote_count"] = 0
        
        # In movies_enriched.parquet, movie_id is the column name
        if "movieId" in movies_df.columns:
            movies_df = movies_df.rename(columns={"movieId": "movie_id"})
        
        movies_meta = movies_df.set_index("movie_id")
        movie_id_to_idx = {mid: i for i, mid in enumerate(movies_meta.index)}
        missing_movie_idx = len(movie_id_to_idx)

        # Vectorize genres
        genres_as_lists = movies_meta["genres"]
        # Ensure all elements are lists or arrays for MultiLabelBinarizer
        genres_as_lists = [g.tolist() if isinstance(g, np.ndarray) else (g if isinstance(g, list) else []) for g in genres_as_lists]
        
        all_genres = sorted({genre.lower() for sublist in genres_as_lists for genre in sublist if genre})
        genre_binarizer = MultiLabelBinarizer(classes=all_genres)
        
        # Binarizer expects list of lists with lower case if we want to match all_genres
        genres_as_lists_lower = [[genre.lower() for genre in sublist] for sublist in genres_as_lists]
        genre_vectors_matrix_dense = genre_binarizer.fit_transform(genres_as_lists_lower).astype(np.int8)
        
        placeholder_row_g = np.zeros((1, genre_vectors_matrix_dense.shape[1]), dtype=np.int8)
        genre_vectors_matrix = np.vstack([genre_vectors_matrix_dense, placeholder_row_g])

        # Vectorize tags
        tags_df = pd.read_parquet(local_tags_path)
        tags_df.dropna(subset=['tag'], inplace=True)
        tags_df['tag'] = tags_df['tag'].str.lower()
        
        # Use a fixed number of top tags or from config if available
        TOP_N_TAGS = 10000 
        top_tags = tags_df['tag'].value_counts().nlargest(TOP_N_TAGS).index
        tag_binarizer = MultiLabelBinarizer(classes=top_tags.tolist(), sparse_output=True)
        
        tags_filtered = tags_df[tags_df['tag'].isin(top_tags)]
        movie_tags = tags_filtered.groupby("movieId")["tag"].unique()
        movie_tags_aligned = movie_tags.reindex(movies_meta.index)
        
        # Use a list of empty lists for movies with no tags
        movie_tags_filled = [tags if isinstance(tags, (list, np.ndarray)) else [] for tags in movie_tags_aligned]

        tag_vectors_matrix_sparse = tag_binarizer.fit_transform(movie_tags_filled).astype(np.int8)
        placeholder_row_t = scipy.sparse.csr_matrix((1, tag_vectors_matrix_sparse.shape[1]), dtype=np.int8)
        tag_vectors_matrix = scipy.sparse.vstack([tag_vectors_matrix_sparse, placeholder_row_t])

        return cls(
            movies_meta=movies_meta,
            movie_id_to_idx=movie_id_to_idx,
            genre_vectors_matrix=genre_vectors_matrix,
            tag_vectors_matrix=tag_vectors_matrix,
            missing_movie_idx=missing_movie_idx
        )

    def __init__(
        self,
        movies_meta: pd.DataFrame,
        movie_id_to_idx: Dict[int, int],
        genre_vectors_matrix: np.ndarray,
        tag_vectors_matrix: spmatrix,
        missing_movie_idx: int,
    ):
        """
        Initializes with shared-memory data structures pre-calculated by the main process.

        Args:
            movies_meta: DataFrame of movie metadata, indexed by 'movieId'.
            movie_id_to_idx: Mapping from movieId to its row index in the vector matrices.
            genre_vectors_matrix: A dense NumPy array where each row is a movie's genre vector.
            tag_vectors_matrix: A sparse SciPy matrix where each row is a movie's tag vector.
            missing_movie_idx: The index of a placeholder row for movies not found in the map.
        """
        log.debug("Initializing lightweight FeatureBuilder with shared-memory data...")
        self.movies_meta = movies_meta
        self.movie_id_to_idx = movie_id_to_idx
        self.genre_vectors_matrix = genre_vectors_matrix
        self.tag_vectors_matrix = tag_vectors_matrix
        self.missing_movie_idx = missing_movie_idx
        log.debug("FeatureBuilder initialized successfully.")

    def _get_vectors(self, movie_ids: List[int], matrix: np.ndarray) -> np.ndarray:
        """Looks up vectors from a matrix given a list of movie IDs."""
        indices = [self.movie_id_to_idx.get(mid) for mid in movie_ids]
        valid_indices = [idx for idx in indices if idx is not None]

        if not valid_indices:
            from scipy.sparse import csr_matrix
            if isinstance(matrix, spmatrix):
                return csr_matrix((0, matrix.shape[1]), dtype=matrix.dtype)
            else:
                return np.empty((0, matrix.shape[1]), dtype=matrix.dtype)

        return matrix[valid_indices]
    
    def build_features(self, queries_df: pd.DataFrame) -> pd.DataFrame:
        """
        Builds features for a DataFrame of queries and candidates using a memory-optimized
        approach that avoids storing vectors in the DataFrame.
        """
        start_time = time.time()
        log.debug(f"Building features for {len(queries_df)} query-candidate pairs...")

        df = queries_df.copy()

        # --- Create an efficient mapping from each query to a unique integer index ---
        df['query_hash'] = df['query_movie_ids'].apply(tuple)
        unique_hashes = df['query_hash'].unique()
        hash_to_idx = {hash_val: i for i, hash_val in enumerate(unique_hashes)}
        query_indices = df['query_hash'].map(hash_to_idx).to_numpy()

        # --- Aggregate features for unique queries into pre-allocated NumPy arrays ---
        log.debug(f"Aggregating features for {len(unique_hashes)} unique queries...")
        num_unique_queries = len(unique_hashes)
        query_g_vecs_agg = np.zeros((num_unique_queries, self.genre_vectors_matrix.shape[1]), dtype=self.genre_vectors_matrix.dtype)
        query_t_vecs_agg = np.zeros((num_unique_queries, self.tag_vectors_matrix.shape[1]), dtype=self.tag_vectors_matrix.dtype)
        query_avg_rating_agg = np.zeros(num_unique_queries, dtype=np.float32)

        unique_queries_df = df[['query_hash', 'query_movie_ids']].drop_duplicates(subset=['query_hash'])

        for _, row in unique_queries_df.iterrows():
            query_hash, query_movie_ids = row['query_hash'], row['query_movie_ids']
            idx = hash_to_idx[query_hash]

            q_genre_vecs = self._get_vectors(query_movie_ids, self.genre_vectors_matrix)
            if q_genre_vecs.size > 0:
                query_g_vecs_agg[idx] = np.clip(q_genre_vecs.sum(axis=0), 0, 1)

            q_tag_vecs = self._get_vectors(query_movie_ids, self.tag_vectors_matrix)
            if q_tag_vecs.size > 0:
                agg_tag_vector = np.clip(q_tag_vecs.sum(axis=0), 0, 1)
                if isinstance(agg_tag_vector, (spmatrix, np.matrix)):
                    agg_tag_vector = agg_tag_vector.toarray().squeeze()
                query_t_vecs_agg[idx] = agg_tag_vector
            
            q_meta = self.movies_meta.loc[self.movies_meta.index.isin(query_movie_ids)]
            if not q_meta.empty:
                query_avg_rating_agg[idx] = q_meta['vote_average'].mean()

        df['feat_avg_query_rating'] = query_avg_rating_agg[query_indices]

        # --- Candidate Feature Lookup & Overlap Calculation ---
        log.debug("Looking up candidate features and calculating overlaps...")
        candidate_ids = df['candidate_movie_id'].to_list()

        # Use pandas' C-optimized "map" for a significant speedup over the Python loop.
        candidate_indices = pd.Series(candidate_ids).map(self.movie_id_to_idx).fillna(self.missing_movie_idx).astype(np.int64).to_numpy()
        
        candidate_g_vecs = self.genre_vectors_matrix[candidate_indices]
        candidate_t_vecs = self.tag_vectors_matrix[candidate_indices].toarray()

        query_g_vecs_expanded = query_g_vecs_agg[query_indices]
        query_t_vecs_expanded = query_t_vecs_agg[query_indices]

        df['feat_genre_overlap'] = (query_g_vecs_expanded * candidate_g_vecs).sum(axis=1)
        df['feat_tag_overlap'] = (query_t_vecs_expanded * candidate_t_vecs).sum(axis=1)
        
        candidate_meta = self.movies_meta.reindex(candidate_ids)
        df['feat_candidate_avg_rating'] = candidate_meta['vote_average'].values
        df['feat_candidate_rating_count'] = candidate_meta['vote_count'].values

        # --- Final Cleanup ---
        feature_cols = [col for col in df.columns if col.startswith("feat_")]
        final_cols = ['query_movie_ids', 'candidate_movie_id']
        if 'label' in df.columns: final_cols.append('label')
        
        df_final = df.drop(columns=['query_hash']).copy()

        df_final = df_final[final_cols + feature_cols]
        df_final.fillna(0, inplace=True)

        log.info(f"Finished building {len(feature_cols)} features in {time.time() - start_time:.2f} seconds.")
        return df_final