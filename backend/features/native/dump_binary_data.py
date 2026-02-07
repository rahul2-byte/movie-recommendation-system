import pandas as pd
import numpy as np
import struct
import os
import sys
from pathlib import Path
import logging

# Add backend to path to allow imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from common.config import config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

def dump_features_csr(movies_df, tags_df, output_dir):
    """
    Converts movie features (genres, tags, stats) into a flattened CSR (Compressed Sparse Row) binary format.
    Output:
      - features_meta.bin: [num_movies, num_features]
      - features_offsets.bin: [0, start_idx_1, start_idx_2, ...] (size num_movies + 1)
      - features_indices.bin: [feat_idx_1, feat_idx_2, ...] (flat list of indices)
      - features_values.bin: [val_1, val_2, ...] (flat list of values)
    """
    log.info("Building Feature Vocabulary...")
    
    # 1. Vocab Building
    genre_set = set()
    for g_list in movies_df["genres"]:
        if isinstance(g_list, (list, np.ndarray)):
            genre_set.update([g.lower() for g in g_list if g])
    
    genre_vocab = {g: i for i, g in enumerate(sorted(genre_set))}
    genre_offset = 0
    
    # Tags
    tag_counts = tags_df['tag'].str.lower().value_counts()
    top_tags = tag_counts.head(10000).index.tolist()
    tag_vocab = {t: i + len(genre_vocab) for i, t in enumerate(top_tags)}
    
    # Numerical (Year, AvgRating, LogPop)
    num_feat_start = len(genre_vocab) + len(tag_vocab)
    total_dim = num_feat_start + 3
    
    # Mappings
    movie_ids = sorted(movies_df["movie_id"].unique())
    movie_id_to_idx = {mid: i for i, mid in enumerate(movie_ids)}
    
    log.info(f"Vocab Size: {total_dim} (Genres: {len(genre_vocab)}, Tags: {len(tag_vocab)}, Num: 3)")
    
    # 2. Construction
    offsets = [0]
    indices = []
    values = []
    
    # Pre-compute lookups
    movies_df = movies_df.set_index("movie_id")
    # Group tags by movie for fast lookup
    tags_grouped = tags_df.groupby("movieId")["tag"].apply(list)
    
    # Stats for normalization
    min_year = movies_df['release_year'].min()
    max_year = movies_df['release_year'].max()
    max_pop = np.log1p(movies_df['vote_count'].max())
    
    log.info("Constructing CSR arrays...")
    for mid in movie_ids:
        curr_indices = []
        curr_values = []
        
        row = movies_df.loc[mid]
        
        # Genres
        if isinstance(row['genres'], (list, np.ndarray)):
            for g in row['genres']:
                g_lower = g.lower()
                if g_lower in genre_vocab:
                    curr_indices.append(genre_vocab[g_lower])
                    curr_values.append(1.0)
        
        # Tags
        if mid in tags_grouped.index:
            for t in tags_grouped[mid]:
                if pd.isna(t):
                    continue
                t_lower = str(t).lower()
                if t_lower in tag_vocab:
                    curr_indices.append(tag_vocab[t_lower])
                    curr_values.append(1.0)
        
        # Numerical
        # Year
        year = row.get('release_year', 0)
        if year > 0:
            norm_year = (year - min_year) / (max_year - min_year + 1e-5)
            curr_indices.append(num_feat_start)
            curr_values.append(norm_year)
            
        # Rating
        rating = row.get('vote_average', 0)
        curr_indices.append(num_feat_start + 1)
        curr_values.append(rating / 10.0) # Normalize 0-10 -> 0-1
        
        # Popularity
        pop = np.log1p(row.get('vote_count', 0))
        curr_indices.append(num_feat_start + 2)
        curr_values.append(pop / max_pop)
        
        # L2 Normalize
        norm = np.linalg.norm(curr_values)
        if norm > 1e-9:
            curr_values = [v / norm for v in curr_values]
            
        indices.extend(curr_indices)
        values.extend(curr_values)
        offsets.append(len(indices))
        
    # 3. Save to Binary
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    log.info("Writing binary files...")
    
    # Meta: [num_movies, num_features]
    with open(output_dir / "features_meta.bin", "wb") as f:
        f.write(struct.pack("ii", len(movie_ids), total_dim))
        
    # Offsets (int32)
    np.array(offsets, dtype=np.int32).tofile(output_dir / "features_offsets.bin")
    
    # Indices (int32)
    np.array(indices, dtype=np.int32).tofile(output_dir / "features_indices.bin")
    
    # Values (float32)
    np.array(values, dtype=np.float32).tofile(output_dir / "features_values.bin")
    
    # Movie ID Map (for inference mapping)
    np.array(movie_ids, dtype=np.int32).tofile(output_dir / "movie_ids.bin")
    
    return movie_id_to_idx

import pyarrow.parquet as pq

def dump_sequences(seq_path, movie_id_to_idx, output_dir):
    """
    Converts sequences Parquet to raw binary array of int32 using streaming.
    Format: [q1, q2, q3, q4, q5, pos_item]
    """
    log.info(f"Streaming Sequences from {seq_path} to binary...")
    output_path = Path(output_dir) / "train_data.bin"
    
    # Create mapping array for ultra-fast vectorized lookup
    max_id = max(movie_id_to_idx.keys())
    map_arr = np.zeros(max_id + 1, dtype=np.int32)
    for k, v in movie_id_to_idx.items():
        map_arr[k] = v

    pf = pq.ParquetFile(seq_path)
    total_written = 0
    
    # Open file for binary writing
    with open(output_path, "wb") as f:
        for batch in pf.iter_batches(batch_size=1_000_000):
            df = batch.to_pandas()
            # Filter only positives
            df = df[df["label"] == 1]
            if df.empty:
                continue
            
            # 1. Map candidate_movie_id (vectorized)
            # Ensure IDs are within range of map_arr
            cand_ids = df["candidate_movie_id"].values
            valid_mask = cand_ids <= max_id
            df = df[valid_mask]
            if df.empty: continue
            
            pos_mapped = map_arr[df["candidate_movie_id"].values]
            
            # 2. Map query_movie_ids (vectorized)
            # vstack converts list of lists to 2D numpy array [N, 5]
            q_ids_raw = np.vstack(df["query_movie_ids"].values).astype(np.int32)
            # Clip q_ids to valid range for indexing
            q_ids_raw = np.clip(q_ids_raw, 0, max_id)
            q_mapped = map_arr[q_ids_raw]
            
            # 3. Combine into [N, 6]
            batch_data = np.hstack([q_mapped, pos_mapped.reshape(-1, 1)])
            
            # 4. Write raw bytes to disk
            f.write(batch_data.tobytes())
            
            total_written += len(batch_data)
            if total_written % 5_000_000 == 0:
                log.info(f"Streamed {total_written} sequences to binary...")

    log.info(f"Binary Dump Complete. Total sequences: {total_written}")

def main():
    movies_path = Path(config.system.movies_metadata_path)
    tags_path = Path(config.system.tags_path)
    seq_path = Path(config.system.training_sequences_path)
    
    out_dir = Path("backend/data/binary_cache")
    
    # 1. Load Data
    log.info("Loading Dataframes...")
    movies_df = pd.read_parquet(movies_path)
    tags_df = pd.read_parquet(tags_path)
    
    # 2. Dump Features
    movie_id_to_idx = dump_features_csr(movies_df, tags_df, out_dir)
    
    # 3. Dump Sequences
    dump_sequences(seq_path, movie_id_to_idx, out_dir)
    
    log.info("Binary Dump Complete.")

if __name__ == "__main__":
    main()
