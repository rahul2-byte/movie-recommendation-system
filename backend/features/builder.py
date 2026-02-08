import time
import logging
from typing import List, Dict
import numpy as np
import pandas as pd
from scipy.sparse import spmatrix

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

class FeatureBuilder:
    @classmethod
    def from_dataframe(cls, movies_df: pd.DataFrame, tags_path: str):
        from common.model_loader import ensure_local_path
        local_tags_path = ensure_local_path(tags_path)
        return cls._initialize_logic(movies_df, local_tags_path)

    @classmethod
    def from_paths(cls, movies_path: str, tags_path: str):
        from common.model_loader import ensure_local_path
        local_movies_path = ensure_local_path(movies_path)
        local_tags_path = ensure_local_path(tags_path)
        movies_df = pd.read_parquet(local_movies_path)
        return cls._initialize_logic(movies_df, local_tags_path)

    @classmethod
    def _initialize_logic(cls, movies_df: pd.DataFrame, local_tags_path: str):
        from sklearn.preprocessing import MultiLabelBinarizer
        import scipy.sparse
        log.info(f'FeatureBuilder: Initializing from DataFrame and tags at {local_tags_path}...')
        num_cols = ['vote_average', 'vote_count', 'runtime_minutes', 'release_year', 'popularity_score', 'imdb_rating', 'imdb_votes']
        for col in num_cols:
            movies_df[col] = movies_df[col].fillna(0.0) if col in movies_df.columns else 0.0
        movies_meta = movies_df.set_index('movie_id') if 'movie_id' in movies_df.columns else movies_df.set_index('movieId')
        movie_id_to_idx = {mid: i for i, mid in enumerate(movies_meta.index)}
        missing_movie_idx = len(movie_id_to_idx)
        genres_as_lists = [g.tolist() if isinstance(g, np.ndarray) else (g if isinstance(g, list) else []) for g in movies_meta['genres']]
        all_genres = sorted({genre.lower() for sublist in genres_as_lists for genre in sublist if genre})
        genre_binarizer = MultiLabelBinarizer(classes=all_genres)
        genres_as_lists_lower = [[genre.lower() for genre in sublist] for sublist in genres_as_lists]
        genre_vectors_matrix_dense = genre_binarizer.fit_transform(genres_as_lists_lower).astype(np.int8)
        genre_vectors_matrix = np.vstack([genre_vectors_matrix_dense, np.zeros((1, genre_vectors_matrix_dense.shape[1]), dtype=np.int8)])
        tags_df = pd.read_parquet(local_tags_path)
        tags_df.dropna(subset=['tag'], inplace=True)
        tags_df['tag'] = tags_df['tag'].str.lower()
        top_tags = tags_df['tag'].value_counts().nlargest(10000).index
        tag_binarizer = MultiLabelBinarizer(classes=top_tags.tolist(), sparse_output=True)
        tags_filtered = tags_df[tags_df['tag'].isin(top_tags)]
        movie_tags = tags_filtered.groupby('movieId')['tag'].unique().reindex(movies_meta.index)
        movie_tags_filled = [tags if isinstance(tags, (list, np.ndarray)) else [] for tags in movie_tags]
        tag_vectors_matrix_sparse = tag_binarizer.fit_transform(movie_tags_filled).astype(np.int8)
        tag_vectors_matrix = scipy.sparse.vstack([tag_vectors_matrix_sparse, scipy.sparse.csr_matrix((1, tag_vectors_matrix_sparse.shape[1]), dtype=np.int8)])
        return cls(movies_meta, movie_id_to_idx, genre_vectors_matrix, tag_vectors_matrix, missing_movie_idx)

    def __init__(self, movies_meta, movie_id_to_idx, genre_vectors_matrix, tag_vectors_matrix, missing_movie_idx):
        self.movies_meta = movies_meta
        self.movie_id_to_idx = movie_id_to_idx
        self.genre_vectors_matrix = genre_vectors_matrix
        self.tag_vectors_matrix = tag_vectors_matrix
        self.missing_movie_idx = missing_movie_idx

    def _get_vectors(self, movie_ids: List[int], matrix) -> np.ndarray:
        indices = [self.movie_id_to_idx.get(mid) for mid in movie_ids]
        valid_indices = [idx for idx in indices if idx is not None]
        if not valid_indices:
            from scipy.sparse import csr_matrix
            return csr_matrix((0, matrix.shape[1]), dtype=matrix.dtype) if isinstance(matrix, spmatrix) else np.empty((0, matrix.shape[1]), dtype=matrix.dtype)
        return matrix[valid_indices]
    
    def build_features(self, queries_df: pd.DataFrame) -> pd.DataFrame:
        start_time = time.time()
        df = queries_df.copy()
        df['query_hash'] = df['query_movie_ids'].apply(tuple)
        unique_hashes = df['query_hash'].unique()
        hash_to_idx = {hash_val: i for i, hash_val in enumerate(unique_hashes)}
        query_indices = df['query_hash'].map(hash_to_idx).to_numpy()
        num_unique_queries = len(unique_hashes)
        query_g_vecs_agg = np.zeros((num_unique_queries, self.genre_vectors_matrix.shape[1]), dtype=self.genre_vectors_matrix.dtype)
        query_t_vecs_agg = np.zeros((num_unique_queries, self.tag_vectors_matrix.shape[1]), dtype=self.tag_vectors_matrix.dtype)
        query_avg_rating_agg, query_avg_year_agg, query_avg_runtime_agg = np.zeros(num_unique_queries), np.zeros(num_unique_queries), np.zeros(num_unique_queries)
        unique_queries_df = df[['query_hash', 'query_movie_ids']].drop_duplicates(subset=['query_hash'])
        for _, row in unique_queries_df.iterrows():
            qh, qmids = row['query_hash'], row['query_movie_ids']
            idx = hash_to_idx[qh]
            qgv = self._get_vectors(qmids, self.genre_vectors_matrix)
            if qgv.size > 0: query_g_vecs_agg[idx] = np.clip(qgv.sum(axis=0), 0, 1)
            qtv = self._get_vectors(qmids, self.tag_vectors_matrix)
            if qtv.size > 0: 
                agg = np.clip(qtv.sum(axis=0), 0, 1)
                query_t_vecs_agg[idx] = agg.toarray().squeeze() if isinstance(agg, (spmatrix, np.matrix)) else agg
            qm = self.movies_meta.loc[self.movies_meta.index.isin(qmids)]
            if not qm.empty:
                query_avg_rating_agg[idx] = qm['vote_average'].mean()
                query_avg_year_agg[idx] = qm['release_year'].replace(0, np.nan).mean() or 0
                query_avg_runtime_agg[idx] = qm['runtime_minutes'].replace(0, np.nan).mean() or 0
        df['feat_avg_query_rating'], df['feat_avg_query_year'], df['feat_avg_query_runtime'] = query_avg_rating_agg[query_indices], query_avg_year_agg[query_indices], query_avg_runtime_agg[query_indices]
        cids = df['candidate_movie_id'].to_list()
        cindices = pd.Series(cids).map(self.movie_id_to_idx).fillna(self.missing_movie_idx).astype(np.int64).to_numpy()
        cgv, ctv = self.genre_vectors_matrix[cindices], self.tag_vectors_matrix[cindices].toarray()
        qge, qte = query_g_vecs_agg[query_indices], query_t_vecs_agg[query_indices]
        df['feat_genre_overlap'], df['feat_tag_overlap'] = (qge * cgv).sum(axis=1), (qte * ctv).sum(axis=1)
        cm = self.movies_meta.reindex(cids)
        df['feat_candidate_avg_rating'] = cm['vote_average'].values
        df['feat_candidate_rating_count'] = cm['vote_count'].values
        df['feat_candidate_runtime'] = cm['vote_minutes'].values if 'vote_minutes' in cm.columns else cm['runtime_minutes'].values
        df['feat_candidate_year'] = cm['release_year'].values
        df['feat_candidate_popularity'] = cm['popularity_score'].values
        df['feat_candidate_imdb_rating'] = cm['imdb_rating'].values
        df['feat_candidate_imdb_votes'] = cm['imdb_votes'].values
        df['feat_year_diff'], df['feat_runtime_diff'] = np.abs(df['feat_candidate_year'] - df['feat_avg_query_year']), np.abs(df['feat_candidate_runtime'] - df['feat_avg_query_runtime'])
        fcols = [c for c in df.columns if c.startswith('feat_')]
        final_cols = ['query_movie_ids', 'candidate_movie_id']
        df_final = df[final_cols + fcols].fillna(0).copy()
        log.info(f'Finished building {len(fcols)} features in {time.time() - start_time:.2f} seconds.')
        return df_final
