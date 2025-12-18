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
        index_path: Path
    ) -> None:
        self.model_dir = model_dir
        self.user_embeddings = user_embeddings

        self.index = faiss.read_index(str(index_path / "faiss.index"))
        self.item_id_map = json.load(
            open(model_dir / "item_id_map.json", "r")
        )
        self.rev_map = {v: k for k, v in self.item_id_map.items()}

    def retrieve(
        self,
        user_id: int,
        top_k: int,
    ) -> List[Tuple[int, float]]:
        user_vec = self.user_embeddings[user_id].astype(np.float32)
        user_vec = np.expand_dims(user_vec, axis=0)

        scores, indices = self.index.search(user_vec, top_k)

        results: List[Tuple[int, float]] = []
        for idx, score in zip(indices[0], scores[0]):
            if idx < 0:
                continue
            item_id = int(self.rev_map[idx])
            results.append((item_id, float(score)))

        return results
