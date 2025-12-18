import json
from pathlib import Path
from typing import List, Tuple

import faiss
import numpy as np

from .base import BaseRetriever


class ALSRetriever(BaseRetriever):
    """
    User-based ALS retriever.
    Query = user latent vector
    Index = item latent vectors
    """

    name = "als"

    def __init__(
        self,
        model_dir: Path,
        user_embeddings: np.ndarray,
        index_path= Path
    ) -> None:
        self.index = faiss.read_index(str(index_path / "faiss.index"))
        self.user_embeddings = user_embeddings

        item_id_map = json.load(open(model_dir / "item_id_map.json", "r"))
        self.rev_item_id_map = {v: int(k) for k, v in item_id_map.items()}

    def retrieve(self, user_id: int, top_k: int):
        user_vec = self.user_embeddings[user_id].astype(np.float32)
        user_vec = user_vec.reshape(1, -1)

        scores, indices = self.index.search(user_vec, top_k)

        results = []
        for idx, score in zip(indices[0], scores[0]):
            if idx < 0:
                continue

            if idx not in self.rev_item_id_map:
                # This should NEVER happen if pipeline is correct
                raise RuntimeError(
                    f"FAISS index / item_id_map mismatch: idx={idx} not found"
                )

            results.append(
                (self.rev_item_id_map[idx], float(score))
            )

        return results
