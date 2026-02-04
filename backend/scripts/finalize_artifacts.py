import numpy as np
import faiss
import json
import os
import shutil
import sys

# Configuration
NATIVE_DIR = "backend/artifacts/native"
MODELS_DIR = "backend/artifacts/models"

MODELS = [
    {
        "name": "als",
        "bin": "als_item_embeddings.bin",
        "meta": "als_embeddings_meta.txt",
        "ids": "als_movie_ids.txt",
        "dtype": np.float64, # ALS used arma::mat (double)
        "index_type": "IndexFlatIP" 
    },
    {
        "name": "content_based",
        "bin": "content_embeddings.bin",
        "meta": "content_embeddings_meta.txt",
        "ids": "content_movie_ids.txt",
        "dtype": np.float32, # Content used arma::fmat (float)
        "index_type": "IndexFlatIP"
    },
    {
        "name": "two_tower",
        "bin": "two_tower_embeddings.bin",
        "meta": "two_tower_embeddings_meta.txt",
        "ids": "two_tower_movie_ids.txt",
        "dtype": np.float32, # Two-Tower used arma::fmat (float)
        "index_type": "IndexFlatIP"
    },
    {
        "name": "tfidf",
        "bin": "tfidf_matrix.bin",
        "meta": "tfidf_meta.txt",
        "ids": "tfidf_movie_ids.txt",
        "dtype": np.float64, # TF-IDF used arma::mat (double)
        "index_type": "IndexFlatIP"
    }
]

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def load_native_data(config):
    bin_path = os.path.join(NATIVE_DIR, config["bin"])
    meta_path = os.path.join(NATIVE_DIR, config["meta"])
    
    if not os.path.exists(bin_path) or not os.path.exists(meta_path):
        print(f"ERROR: Missing artifacts for {config['name']}")
        return None, None

    # Read dimensions
    with open(meta_path, 'r') as f:
        line = f.readline().split()
        rows = int(line[0])
        cols = int(line[1])
    
    # Load data
    data = np.fromfile(bin_path, dtype=config["dtype"])
    # Armadillo saves Column-Major. Reshape to (Rows, Cols) using Fortran order.
    data = data.reshape((rows, cols), order='F')
    
    # Convert double to float32 for FAISS (FAISS mostly uses float32)
    if data.dtype == np.float64:
        data = data.astype(np.float32)
    
    # Ensure C-contiguous for FAISS
    if not data.flags['C_CONTIGUOUS']:
        data = np.ascontiguousarray(data, dtype=np.float32)
        
    return data, (rows, cols)

def build_faiss_index(data, config):
    print(f"[{config['name']}] Building FAISS index ({data.shape})...")
    
    # Normalize for Cosine Similarity (IndexFlatIP)
    # Note: TF-IDF and Content-Based were normalized in C++.
    # ALS and Two-Tower output might not be strictly unit norm yet (Two-Tower was just W*x).
    # Safe to re-normalize.
    faiss.normalize_L2(data)
    
    d = data.shape[1]
    index = faiss.IndexFlatIP(d)
    index.add(data)
    
    return index

def save_artifacts(model_name, index, ids_list):
    target_dir = os.path.join(MODELS_DIR, model_name)
    ensure_dir(target_dir)
    
    # 1. Save Index
    index_path = os.path.join(target_dir, "faiss.index")
    faiss.write_index(index, index_path)
    print(f"[{model_name}] Saved index to {index_path}")
    
    # 2. Save ID Mapping (JSON)
    # The native file is a list of IDs corresponding to matrix rows.
    # Backend expects: {"movie_id": index}
    mapping = {int(mid): idx for idx, mid in enumerate(ids_list)}
    
    mapping_path = os.path.join(target_dir, "movie_id_to_idx.json")
    with open(mapping_path, 'w') as f:
        json.dump(mapping, f)
    print(f"[{model_name}] Saved mapping to {mapping_path}")
    
    # 3. Clean up old/unused files if necessary?
    # For now, we overwrite. 
    # Python backend might look for 'item_embeddings.npy' for direct lookup.
    # We should probably save the embeddings as .npy too for the Retriever to load efficiently if it needs raw vectors.
    # ALSRetriever uses: self.item_embeddings = np.load(...)
    # So we MUST save .npy.
    
    # Determine standard NPY name based on existing patterns
    npy_name = "item_embeddings.npy"
    if model_name == "tfidf": npy_name = "tfidf_matrix.npy" # Special case if needed? Or standardized?
    # Backend code check:
    # ALS: "embeddings_path" (config) -> likely 'item_embeddings.npy'
    # Content: "embeddings_path" -> likely 'item_embeddings.npy'
    # TwoTower: "embeddings_path" -> likely 'item_embeddings.npy'
    # TFIDF: "matrix_path" -> likely 'tfidf_matrix.npz' usually, but we can switch to npy or standard.
    # Let's standardize to 'item_embeddings.npy' for all vector models if possible, or stick to config.
    
    # For compatibility with current backend config, let's assume 'item_embeddings.npy' is standard.
    # TFIDF backend expects CSR matrix usually?
    # TfidfRetriever: self.tfidf_matrix = load_npz(...)
    # BUT our native TFIDF is dense now!
    # We should save as .npy and update TfidfRetriever to load .npy (dense).
    
    npy_path = os.path.join(target_dir, "item_embeddings.npy")
    
    # For TF-IDF, let's check what the backend expects.
    # The user said "update backend loaders", so we have freedom to standardize.
    
    # We actually need the raw embeddings in memory for mapping query seeds to vectors.
    # So we save the data array as .npy.
    # However, we need to reload the data because 'data' was modified in place by faiss.normalize_L2?
    # Yes, faiss.normalize_L2 modifies in place.
    # But normalized vectors are what we want for retrieval usually.
    
    # Actually, for query construction:
    # Query = Mean(Seed Embeddings).
    # Then Normalize(Query).
    # Then Search.
    # If we average normalized seed embeddings, it works fine (Directional Mean).
    
    np.save(npy_path, np.fromfile(os.path.join(NATIVE_DIR, MODELS[0]['bin']), dtype=np.float64)) # Placeholder load?
    # Wait, passing 'data' (which is normalized) is fine.
    np.save(npy_path, data) # 'data' variable from build_faiss_index scope? No, need to pass it.
    
    print(f"[{model_name}] Saved embeddings to {npy_path}")

def process_model(config):
    # 1. Load IDs
    id_path = os.path.join(NATIVE_DIR, config["ids"])
    if not os.path.exists(id_path):
        print(f"ERROR: ID file missing for {config['name']}")
        return
    
    with open(id_path, 'r') as f:
        ids = [line.strip() for line in f if line.strip()]
        
    # 2. Load Data
    data, dims = load_native_data(config)
    if data is None: return
    
    if data.shape[0] != len(ids):
        print(f"ERROR: Dimension mismatch for {config['name']}. Data {data.shape} vs IDs {len(ids)}")
        return

    # 3. Build Index (Modifies data in-place for normalization)
    index = build_faiss_index(data, config)
    
    # 4. Save Artifacts (Index + JSON Map + NPY)
    # We pass 'data' which is now normalized.
    target_dir = os.path.join(MODELS_DIR, config["name"])
    ensure_dir(target_dir)
    
    # Index
    faiss.write_index(index, os.path.join(target_dir, "faiss.index"))
    
    # Map
    mapping = {int(mid): idx for idx, mid in enumerate(ids)}
    with open(os.path.join(target_dir, "movie_id_to_idx.json"), 'w') as f:
        json.dump(mapping, f)
        
    # NPY (Standardize name to 'item_embeddings.npy')
    # For TF-IDF, the backend might expect sparse, but we now have dense.
    # We will update backend later. For now, save as dense npy.
    np.save(os.path.join(target_dir, "item_embeddings.npy"), data)
    
    print(f"[{config['name']}] Artifacts finalized in {target_dir}")

def main():
    print("--- Finalizing Artifacts ---")
    ensure_dir(MODELS_DIR)
    
    for config in MODELS:
        try:
            process_model(config)
        except Exception as e:
            print(f"ERROR processing {config['name']}: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()
