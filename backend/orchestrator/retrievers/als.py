import json
from pathlib import Path
from typing import List, Tuple

import faiss
import numpy as np

from .base import BaseRetriever


class ALSRetriever(BaseRetriever):
    name = "als"

    def __init__(
        self,
        model_dir: Path,
        user_embeddings: np.ndarray,
        index_path: Path,
    ) -> None:
        self.user_embeddings = user_embeddings.astype(np.float32)

        # FAISS index built on INTERNAL item indices
        self.index = faiss.read_index(str(index_path / "faiss.index"))

        # -------------------------------------------------
        # Load ID maps (saved as lists)
        # -------------------------------------------------
        with open(model_dir / "id_maps.json", "r") as f:
            id_maps = json.load(f)

        user_id_list = id_maps["user_id_map"]
        item_id_list = id_maps["item_id_map"]

        # external_user_id → internal_user_index
        self.user_id_map = {
            int(ext_id): int(idx)
            for idx, ext_id in enumerate(user_id_list)
        }

        # internal_item_index → external_item_id
        self.rev_item_id_map = {
            int(idx): int(ext_id)
            for idx, ext_id in enumerate(item_id_list)
        }

        # -------------------------------------------------
        # Fail-fast sanity checks
        # -------------------------------------------------
        assert self.user_embeddings.shape[0] == len(self.user_id_map), (
            "ALS user embeddings and ID map size mismatch"
        )

    def retrieve(self, user_id: int, top_k: int) -> List[Tuple[int, float]]:
        # -------------------------------------------------
        # Guard: user unseen during ALS training
        # -------------------------------------------------
        if user_id not in self.user_id_map:
            return []

        user_idx = self.user_id_map[user_id]

        user_vec = self.user_embeddings[user_idx].reshape(1, -1)

        scores, indices = self.index.search(user_vec, top_k)

        return [
            (self.rev_item_id_map[int(idx)], float(score))
            for idx, score in zip(indices[0], scores[0])
            if idx >= 0
        ]
