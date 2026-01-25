import json
from pathlib import Path
from typing import List, Tuple

import faiss
import numpy as np

from .base import BaseRetriever


class MetaBasedRetriever(BaseRetriever):
    """
    Seed-aware semantic (metadata / item-embedding) retriever.
    """

    name = "meta"

    def __init__(
        self,
        model_dir: Path,
        index_path: Path,
    ) -> None:
        self.model_dir = model_dir

        self.index = faiss.read_index(str(index_path / "faiss.index"))

        self.item_id_map = json.load(
            open(model_dir / "item_id_map.json", "r")
        )
        self.rev_map = {v: int(k) for k, v in self.item_id_map.items()}

        self.item_embeddings = np.load(
            model_dir / "item_embeddings.npy"
        ).astype(np.float32)

        self.centroid = self.item_embeddings.mean(
            axis=0, keepdims=True
        )

    def retrieve(
        self,
        user_id: int,
        top_k: int,
        recent_item_ids: List[int] | None = None,
    ) -> List[Tuple[int, float]]:

        seed_vectors = [
            self.item_embeddings[self.item_id_map[str(i)]]
            for i in (recent_item_ids or [])
            if str(i) in self.item_id_map
        ]

        if seed_vectors:
            query = np.mean(seed_vectors, axis=0, keepdims=True)
        else:
            query = self.centroid

        scores, indices = self.index.search(query, top_k)

        return [
            (self.rev_map[int(idx)], float(score))
            for idx, score in zip(indices[0], scores[0])
            if idx >= 0
        ]
