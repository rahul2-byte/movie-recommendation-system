import sys
import numpy as np
import faiss
import lightgbm as lgb
import json
import logging
from pathlib import Path

# Add backend to sys.path
BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

# Force LOCAL for path resolution
import os
os.environ["ENVIRONMENT"] = "LOCAL"

from configs import settings
from common.config import config
from common.logger import get_logger

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("model_verifier")

def verify_retrieval_model(name, artifact_config):
    log.info(f"--- Verifying {name} ---")
    
    # 1. Embeddings
    emb_path = Path(artifact_config.embeddings_path)
    if not emb_path.exists():
        log.error(f"FAIL: Embeddings file missing at {emb_path}")
        return False
    
    try:
        embeddings = np.load(emb_path)
        log.info(f"Embeddings loaded. Shape: {embeddings.shape}")
        if embeddings.size == 0:
            log.error("FAIL: Embeddings array is empty.")
            return False
    except Exception as e:
        log.error(f"FAIL: Could not load embeddings: {e}")
        return False

    # 2. FAISS Index
    index_path = Path(artifact_config.faiss_index_path)
    if not index_path.exists():
        log.error(f"FAIL: FAISS index missing at {index_path}")
        return False
        
    try:
        index = faiss.read_index(str(index_path))
        log.info(f"FAISS Index loaded. NTotal: {index.ntotal}")
        if index.ntotal == 0:
            log.error("FAIL: FAISS Index is empty.")
            return False
        if index.ntotal != embeddings.shape[0]:
            log.error(f"FAIL: Mismatch. Index size {index.ntotal} != Embeddings rows {embeddings.shape[0]}")
            return False
            
        # Dummy Search
        D, I = index.search(embeddings[:1], 5)
        log.info(f"Dummy search successful. Top 1 ID: {I[0][0]}")
    except Exception as e:
        log.error(f"FAIL: FAISS Error: {e}")
        return False

    # 3. ID Map
    map_path = Path(artifact_config.id_map_path)
    if not map_path.exists():
        log.error(f"FAIL: ID Map missing at {map_path}")
        return False
        
    try:
        with open(map_path, 'r') as f:
            id_map = json.load(f)
        log.info(f"ID Map loaded. Entries: {len(id_map)}")
        if len(id_map) != index.ntotal:
            log.error(f"FAIL: Map size {len(id_map)} != Index size {index.ntotal}")
            return False
    except Exception as e:
        log.error(f"FAIL: Map load error: {e}")
        return False

    log.info(f"PASS: {name} is valid.\n")
    return True

def verify_ranker():
    log.info("--- Verifying Ranker ---")
    model_path = Path(settings.RANKER_MODEL_URI) / "lgbm_lambdarank.txt"
    if not model_path.exists():
        log.error(f"FAIL: Ranker model missing at {model_path}")
        return False
        
    try:
        booster = lgb.Booster(model_file=str(model_path))
        log.info(f"Ranker loaded. Features: {booster.num_feature()}")
        if booster.num_feature() == 0:
            log.error("FAIL: Ranker has 0 features.")
            return False
            
        # Dummy Predict
        dummy_input = np.random.rand(1, booster.num_feature())
        score = booster.predict(dummy_input)
        log.info(f"Dummy prediction score: {score[0]}")
    except Exception as e:
        log.error(f"FAIL: Ranker load error: {e}")
        return False
        
    log.info("PASS: Ranker is valid.\n")
    return True

def main():
    success = True
    
    # Check Retrieval Models from Settings
    artifacts = config.system.retrieval_artifacts
    
    # 1. TF-IDF
    if not verify_retrieval_model("TF-IDF", artifacts.tfidf): success = False
    
    # 2. Content-Based
    if not verify_retrieval_model("Content-Based", artifacts.content_based): success = False
    
    # 3. ALS
    if not verify_retrieval_model("ALS", artifacts.als): success = False
    
    # 4. Two-Tower
    if not verify_retrieval_model("Two-Tower", artifacts.two_tower): success = False
    
    # 5. Ranker
    if not verify_ranker(): success = False
    
    if success:
        log.info("ALL MODELS VERIFIED SUCCESSFULLY.")
        sys.exit(0)
    else:
        log.error("SOME MODELS FAILED VERIFICATION.")
        sys.exit(1)

if __name__ == "__main__":
    main()
