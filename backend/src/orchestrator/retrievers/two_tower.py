import json
from pathlib import Path
from typing import List, Tuple

import faiss
import numpy as np

from .base import BaseRetriever


class TwoTowerRetriever(BaseRetriever):
    """
    FAISS-backed Two-Tower retriever.
    Uses cosine similarity (normalized embeddings).
    """

    name = "two_tower"

    def __init__(
        self,
        model_dir: Path,
        user_embeddings: np.ndarray,
        index_path: Path,
    ) -> None:
        self.model_dir = model_dir
        self.user_embeddings = user_embeddings.astype(np.float32)

        # -------------------------------------------------
        # Load FAISS index (built on INTERNAL item indices)
        # -------------------------------------------------
        self.index = faiss.read_index(str(index_path / "faiss.index"))

        # -------------------------------------------------
        # Load ID maps (saved as lists)
        # id_maps.json structure:
        # {
        #   "user_id_map": [external_user_id_0, external_user_id_1, ...],
        #   "item_id_map": [external_item_id_0, external_item_id_1, ...]
        # }
        # -------------------------------------------------
        with open(model_dir / "id_maps.json", "r") as f:
            id_maps = json.load(f)

        user_id_list = id_maps["user_id_map"]
        item_id_list = id_maps["item_id_map"]

        # -------------------------------------------------
        # Build explicit mappings
        # -------------------------------------------------
        # external_user_id -> internal_user_index
        self.user_id_map = {
            int(ext_id): int(idx)
            for idx, ext_id in enumerate(user_id_list)
        }

        # internal_item_index -> external_item_id
        self.rev_item_id_map = {
            int(idx): int(ext_id)
            for idx, ext_id in enumerate(item_id_list)
        }

        # -------------------------------------------------
        # Defensive sanity checks (FAIL FAST)
        # -------------------------------------------------
        assert len(self.user_id_map) == self.user_embeddings.shape[0], (
            "User ID map size does not match user embeddings"
        )


    def retrieve(self, user_id: int, top_k: int):
        # -------------------------------------------------
        # Map external user_id → internal index
        # -------------------------------------------------
        if user_id not in self.user_id_map:
            return []  # cold user or filtered during training

        user_idx = self.user_id_map[user_id]
        
        assert user_idx < self.user_embeddings.shape[0]

        user_vec = self.user_embeddings[user_idx].reshape(1, -1)

        scores, indices = self.index.search(user_vec, top_k)

        return [
            (self.rev_item_id_map[int(idx)], float(score))
            for idx, score in zip(indices[0], scores[0])
            if idx >= 0
        ]
