import os
import sys
from pathlib import Path

# Add backend to path to allow imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

import struct

import numpy as np
import pandas as pd
from common.config import config


def main():
    ratings_path = Path(config.system.ratings_path)
    if not ratings_path.exists():
        sys.stderr.write(f"Error: {ratings_path} not found.\n")
        sys.exit(1)

    df = pd.read_parquet(ratings_path)

    unique_movies = df["movieId"].unique()
    unique_users = df["userId"].unique()

    movie_to_idx = {int(m): i for i, m in enumerate(unique_movies)}
    user_to_idx = {int(u): i for i, u in enumerate(unique_users)}

    num_movies = len(unique_movies)
    num_users = len(unique_users)
    num_interactions = len(df)

    # 1. Write Header (num_movies, num_users, num_interactions)
    sys.stdout.buffer.write(struct.pack("iiq", num_movies, num_users, num_interactions))

    # 2. Write Movie ID Mapping (idx to original movieId)
    idx_to_movie = np.array(unique_movies, dtype="int32")
    sys.stdout.buffer.write(idx_to_movie.tobytes())

    # 3. Write COO Vectors
    # Map IDs to indices
    item_indices = df["movieId"].map(movie_to_idx).to_numpy(dtype="int32")
    user_indices = df["userId"].map(user_to_idx).to_numpy(dtype="int32")

    sys.stdout.buffer.write(item_indices.tobytes())
    sys.stdout.buffer.write(user_indices.tobytes())

    sys.stderr.write(
        f"ALS Bridge: Streamed {num_interactions} interactions for {num_movies} movies and {num_users} users.\n"
    )


if __name__ == "__main__":
    main()
