import numpy as np
import os
import sys

ARTIFACTS_DIR = "backend/artifacts/native"

# Map C++ naming to Python types
# ALS, TF-IDF used arma::mat (double)
# Content, Two-Tower used arma::fmat (float)
MODELS = [
    {
        "name": "ALS",
        "bin": "als_item_embeddings.bin",
        "meta": "als_embeddings_meta.txt",
        "ids": "als_movie_ids.txt",
        "dtype": np.float64
    },
    {
        "name": "TF-IDF",
        "bin": "tfidf_matrix.bin",
        "meta": "tfidf_meta.txt",
        "ids": "tfidf_movie_ids.txt",
        "dtype": np.float64
    },
    {
        "name": "Content-Based",
        "bin": "content_embeddings.bin",
        "meta": "content_embeddings_meta.txt",
        "ids": "content_movie_ids.txt",
        "dtype": np.float32
    },
    {
        "name": "Two-Tower",
        "bin": "two_tower_embeddings.bin",
        "meta": "two_tower_embeddings_meta.txt",
        "ids": "two_tower_movie_ids.txt",
        "dtype": np.float32
    }
]

def validate_model(model_config):
    name = model_config["name"]
    print(f"--- Validating {name} ---")
    
    bin_path = os.path.join(ARTIFACTS_DIR, model_config["bin"])
    meta_path = os.path.join(ARTIFACTS_DIR, model_config["meta"])
    id_path = os.path.join(ARTIFACTS_DIR, model_config["ids"])

    # 1. Check Files
    if not os.path.exists(bin_path):
        print(f"ERROR: {bin_path} not found.")
        return False
    if not os.path.exists(meta_path):
        print(f"ERROR: {meta_path} not found.")
        return False
    if not os.path.exists(id_path):
        print(f"ERROR: {id_path} not found.")
        return False

    # 2. Read Metadata (Dimensions)
    try:
        with open(meta_path, 'r') as f:
            line = f.readline().split()
            rows = int(line[0])
            cols = int(line[1])
        print(f"Meta Dimensions: {rows} x {cols}")
    except Exception as e:
        print(f"ERROR: Failed to read metadata: {e}")
        return False

    # 3. Load Binary Data
    try:
        # Armadillo saves in Column-Major order (Fortran style)
        data = np.fromfile(bin_path, dtype=model_config["dtype"])
        
        # Check total size
        expected_size = rows * cols
        if data.size != expected_size:
            print(f"ERROR: File size mismatch. Expected {expected_size} elements, got {data.size}.")
            return False
            
        # Reshape using Fortran order
        data = data.reshape((rows, cols), order='F')
        
        print(f"Embeddings Shape: {data.shape}")
        print(f"Embeddings Mean: {data.mean():.4f}, Std: {data.std():.4f}")
        
        if np.isnan(data).any():
            print("WARNING: Embeddings contain NaNs!")
            return False
            
    except Exception as e:
        print(f"ERROR: Failed to load binary file: {e}")
        return False

    # 4. Validate against IDs
    try:
        with open(id_path, 'r') as f:
            ids = [line.strip() for line in f if line.strip()]
        print(f"ID Count: {len(ids)}")
        
        if len(ids) != data.shape[0]:
            print(f"ERROR: ID count ({len(ids)}) does not match rows ({data.shape[0]})")
            return False
            
    except Exception as e:
        print(f"ERROR: Failed to load id file: {e}")
        return False
        
    print(f"{name} Validated Successfully.\n")
    return True

def main():
    success = True
    for config in MODELS:
        if not validate_model(config):
            success = False

    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()