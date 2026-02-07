import numpy as np
import faiss
import json
import os
from pathlib import Path
import struct

PROJECT_ROOT = Path(__file__).resolve().parent.parent
NATIVE_DIR = PROJECT_ROOT / "artifacts" / "native"
MODELS_DIR = PROJECT_ROOT / "artifacts" / "models"
BINARY_CACHE = PROJECT_ROOT / "data" / "binary_cache"

def load_ids_from_txt(path):
    with open(path, 'r') as f:
        return [int(line.strip()) for line in f if line.strip()]

def load_ids_from_bin(path):
    # Assuming int32 sequence
    ids = np.fromfile(path, dtype=np.int32)
    return ids.tolist()

def load_arma_bin(bin_path, meta_path=None, dtype=np.float64, shape=None):
    if meta_path:
        with open(meta_path, 'r') as f:
            header = f.readline().split()
            rows, cols = int(header[0]), int(header[1])
    elif shape:
        rows, cols = shape
    else:
        raise ValueError("Must provide meta_path or shape")

    data = np.fromfile(bin_path, dtype=dtype)
    
    # Armadillo stores in Column-Major order (Fortran)
    # We load it and reshape to (Rows, Cols) respecting F order
    try:
        data = data.reshape((rows, cols), order='F') 
    except ValueError as e:
        print(f"Error reshaping {bin_path}: {e}. Expected {rows}x{cols}={rows*cols}, got {data.size}")
        raise e
    
    # Check C-Contiguous
    if not data.flags['C_CONTIGUOUS']:
        data = np.ascontiguousarray(data)
    return data

def process_model(name, bin_file, meta_file, id_file, dtype, id_format='txt'):
    print(f"Processing {name}...")
    target_dir = MODELS_DIR / name
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Load IDs
    if id_format == 'txt':
        id_path = NATIVE_DIR / id_file
        if not id_path.exists():
             print(f"Skipping {name}: ID file {id_path} not found")
             return
        ids = load_ids_from_txt(id_path)
    else:
        id_path = BINARY_CACHE / id_file
        if not id_path.exists():
             print(f"Skipping {name}: ID file {id_path} not found")
             return
        ids = load_ids_from_bin(id_path)
        
    # 2. Load Matrix
    bin_path = NATIVE_DIR / bin_file
    if not bin_path.exists():
        print(f"Skipping {name}: Bin file {bin_path} not found")
        return

    if name == 'two_tower':
        rows = len(ids)
        cols = 64
        data = load_arma_bin(bin_path, dtype=dtype, shape=(rows, cols))
    else:
        data = load_arma_bin(bin_path, meta_path=NATIVE_DIR / meta_file, dtype=dtype)
        
    if data.shape[0] != len(ids):
        print(f"WARNING: Shape mismatch {data.shape} vs {len(ids)} IDs. Truncating data to match IDs.")
        data = data[:len(ids)]
    
    # 3. Normalize & Index
    # Cast to float32 for FAISS
    data_f32 = data.astype(np.float32)
    faiss.normalize_L2(data_f32)
    
    index = faiss.IndexFlatIP(data_f32.shape[1])
    index.add(data_f32)
    
    # 4. Save
    faiss.write_index(index, str(target_dir / "faiss.index"))
    
    mapping = {int(mid): i for i, mid in enumerate(ids)}
    with open(target_dir / "movie_id_to_idx.json", 'w') as f:
        json.dump(mapping, f)
        
    np.save(target_dir / "item_embeddings.npy", data_f32)
    print(f"Saved {name} to {target_dir}")

def main():
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    # ALS
    process_model("als", "als_item_embeddings.bin", "als_embeddings_meta.txt", "als_movie_ids.txt", np.float64)
    
    # Content
    process_model("content_based", "content_embeddings.bin", "content_embeddings_meta.txt", "content_movie_ids.txt", np.float32)
    
    # TF-IDF
    process_model("tfidf", "tfidf_matrix.bin", "tfidf_meta.txt", "tfidf_movie_ids.txt", np.float64)
    
    # Two-Tower
    process_model("two_tower", "two_tower_embeddings.bin", None, "movie_ids.bin", np.float32, id_format='bin')

if __name__ == "__main__":
    main()