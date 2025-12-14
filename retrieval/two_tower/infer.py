# src/retrieval/two_tower/infer.py
"""
Inference helpers for Two-Tower model.

Provides:
- batch extraction of item embeddings (memory-friendly)
- utility to compute a user embedding from user id or recent history
- optional FAISS index builder (if faiss installed)
- functions persist embeddings and minimal metadata (numpy + json)

Notes:
- Item embeddings extraction is done in batches to limit GPU/CPU memory use.
- User embeddings may be computed online (from user_id) or precomputed & cached (recommended).
"""

import os
import json
from typing import Iterable, Optional

import numpy as np
import torch
from tqdm import tqdm

try:
    import faiss
    FAISS_AVAILABLE = True
except Exception:
    FAISS_AVAILABLE = False

from .model import TwoTower


def load_model_checkpoint(checkpoint_path: str, device: str = "cpu") -> TwoTower:
    """Load TwoTower checkpoint and return model on device."""
    ckpt = torch.load(checkpoint_path, map_location=device)
    # We assume checkpoint does not include num_users/num_items metadata.
    # The caller should create a model with matching shapes and call load_state_dict.
    # For convenience, store a minimal metadata file alongside checkpoint (e.g., meta.json).
    # We'll try to detect a meta.json in same folder.
    model_meta_path = os.path.join(os.path.dirname(checkpoint_path), "meta.json")
    if not os.path.exists(model_meta_path):
        raise FileNotFoundError(f"Missing meta.json beside checkpoint {checkpoint_path}")
    meta = json.load(open(model_meta_path, "r"))
    model = TwoTower(
        num_users=meta["num_users"],
        num_items=meta["num_items"],
        emb_dim=meta.get("emb_dim", 128),
        user_mlp=meta.get("user_mlp"),
        item_mlp=meta.get("item_mlp"),
        dropout=meta.get("dropout", 0.1),
    )
    model.load_state_dict(ckpt["model_state_dict"])
    model.to(device)
    model.eval()
    return model


def extract_item_embeddings(
    model: TwoTower,
    device: str,
    out_path: str,
    batch_size: int = 4096,
):
    """
    Extract item embeddings and save as numpy array .npy file.

    Args:
        model: loaded TwoTower model (on device)
        device: 'cpu' or 'cuda'
        out_path: path to save embeddings (npy)
        batch_size: number of items processed per batch
    """
    model.to(device)
    model.eval()

    num_items = model.item_tower.id_emb.num_embeddings
    emb_dim = model.item_tower.id_emb.embedding_dim
    out = np.zeros((num_items, emb_dim), dtype=np.float32)

    with torch.no_grad():
        for start in tqdm(range(0, num_items, batch_size), desc="extract_items"):
            end = min(start + batch_size, num_items)
            ids = torch.arange(start, end, dtype=torch.long, device=device)
            item_emb = model.encode_items(ids)  # (B, D) normalized
            out[start:end] = item_emb.cpu().numpy()
    # save
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    np.save(out_path, out)
    meta_path = out_path + ".meta.json"
    json.dump({"num_items": num_items, "emb_dim": emb_dim}, open(meta_path, "w"), indent=2)
    return out_path


def extract_user_embeddings(
    model: TwoTower,
    device: str,
    user_ids: Iterable[int],
    out_path: str,
    batch_size: int = 4096,
):
    """
    Extract user embeddings for a list/iterable of user indices (encoded 0..N-1).
    Save to .npy (rows aligned with provided user_ids order).
    """
    model.to(device)
    model.eval()

    user_ids = list(user_ids)
    embed_dim = model.user_tower.id_emb.embedding_dim
    out = np.zeros((len(user_ids), embed_dim), dtype=np.float32)

    with torch.no_grad():
        for start in tqdm(range(0, len(user_ids), batch_size), desc="extract_users"):
            end = min(start + batch_size, len(user_ids))
            batch_u = torch.tensor(user_ids[start:end], dtype=torch.long, device=device)
            u_emb = model.encode_users(batch_u)
            out[start:end] = u_emb.cpu().numpy()
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    np.save(out_path, out)
    return out_path


def build_faiss_index(
    embeddings_path: str,
    index_path: str,
    index_type: str = "ivfflat",
    nlist: int = 4096,
    ef_search: Optional[int] = None,
):
    """
    Build a FAISS index and save it.

    - index_type: 'flat' | 'ivfflat' | 'hnsw' ; default ivfflat (fast & tunable)
    - nlist: number of coarse clusters for IVF
    - ef_search: for HNSW use
    """

    if not FAISS_AVAILABLE:
        raise RuntimeError("faiss is not installed. Install faiss-cpu or faiss-gpu to build index.")

    xb = np.load(embeddings_path).astype(np.float32)
    dim = xb.shape[1]
    # normalize for cosine using inner product
    faiss.normalize_L2(xb)

    if index_type == "flat":
        index = faiss.IndexFlatIP(dim)
        index.add(xb)
    elif index_type == "ivfflat":
        quantizer = faiss.IndexFlatIP(dim)
        index = faiss.IndexIVFFlat(quantizer, dim, nlist, faiss.METRIC_INNER_PRODUCT)
        # train then add — training needs sample vectors
        # use subset for training (up to 100k or all if small)
        train_sample = xb[np.random.choice(len(xb), size=min(len(xb), 100000), replace=False)]
        index.train(train_sample)
        index.add(xb)
    elif index_type == "hnsw":
        # HNSW is great for dynamic add/remove and high recall
        index = faiss.IndexHNSWFlat(dim, 32)  # M=32
        index.hnsw.efConstruction = 200
        index.add(xb)
        if ef_search:
            index.hnsw.efSearch = ef_search
    else:
        raise ValueError(f"Unknown index_type={index_type}")

    # save index
    os.makedirs(os.path.dirname(index_path), exist_ok=True)
    faiss.write_index(index, index_path)
    return index_path


def compute_dot_retrieval(user_emb: np.ndarray, item_embs: np.ndarray, topk: int = 100):
    """
    Simple CPU fallback retrieval by dot-product between a single user emb and item_embs.
    item_embs should be normalized if cosine-like behavior desired.
    Returns indices and scores arrays.
    """
    assert user_emb.ndim == 1
    scores = item_embs.dot(user_emb)
    topk_idx = np.argpartition(-scores, topk)[:topk]
    topk_sorted = topk_idx[np.argsort(-scores[topk_idx])]
    return topk_sorted, scores[topk_sorted]


if __name__ == "__main__":
    # quick CLI example for usage (not intended for heavy automation)
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", required=True, help="path to two_tower_last.pt or best")
    parser.add_argument("--meta", required=True, help="path to meta.json describing num_items/num_users")
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--out_item_emb", default="models/two_tower/item_embs.npy")
    parser.add_argument("--build_faiss", action="store_true")
    parser.add_argument("--faiss_index_path", default="models/two_tower/faiss.index")
    args = parser.parse_args()

    # load checkpoint with separate meta (to keep checkpoint light)
    # meta.json structure example:
    # { "num_users": 100000, "num_items": 60000, "emb_dim": 128, "user_mlp":[256], "item_mlp":[256] }
    meta = json.load(open(args.meta, "r"))
    # load model and dump item embeddings
    model = TwoTower(
        num_users=meta["num_users"],
        num_items=meta["num_items"],
        emb_dim=meta.get("emb_dim", 128),
        user_mlp=meta.get("user_mlp"),
        item_mlp=meta.get("item_mlp"),
        dropout=meta.get("dropout", 0.1),
    )
    ckpt = torch.load(args.checkpoint, map_location=args.device)
    model.load_state_dict(ckpt["model_state_dict"])
    model.to(args.device)
    model.eval()

    print("[infer] extracting item embeddings ...")
    extract_item_embeddings(model, device=args.device, out_path=args.out_item_emb, batch_size=4096)
    print(f"[infer] item embeddings saved to {args.out_item_emb}")

    if args.build_faiss:
        if not FAISS_AVAILABLE:
            print("[infer] faiss not installed; skipping indexing.")
        else:
            print("[infer] building faiss index ...")
            build_faiss_index(args.out_item_emb, args.faiss_index_path, index_type="ivfflat", nlist=4096)
            print(f"[infer] saved faiss index to {args.faiss_index_path}")
