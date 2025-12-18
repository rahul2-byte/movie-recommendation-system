import json
from pathlib import Path
from typing import Iterable, List, Tuple

import faiss
import numpy as np

from .base import BaseRetriever


class ItemCFRetriever(BaseRetriever):
    """
    Item–Item CF using ALS item embeddings.

    Query = recent item embeddings
    Index = ALS item FAISS index
    """

    name = "item_cf"

    def __init__(
        self,
        model_dir: Path,
        item_embeddings: np.ndarray,
        recent_item_ids: Iterable[int],
        index_path: Path
    ) -> None:
        self.index = faiss.read_index(str(index_path / "faiss.index"))
        self.item_embeddings = item_embeddings

        item_id_map = json.load(open(model_dir / "item_id_map.json", "r"))
        self.item_id_map = {int(k): v for k, v in item_id_map.items()}
        self.rev_item_id_map = {v: int(k) for k, v in item_id_map.items()}

        self.recent_item_ids = list(recent_item_ids)

    def retrieve(self, user_id: int, top_k: int) -> List[Tuple[int, float]]:
        if not self.recent_item_ids:
            return []

        seed_indices = [
            self.item_id_map[i]
            for i in self.recent_item_ids
            if i in self.item_id_map
        ]

        if not seed_indices:
            return []

        seed_vecs = self.item_embeddings[seed_indices].astype(np.float32)

        scores, indices = self.index.search(seed_vecs, top_k)

        agg_scores = {}

        for row_scores, row_indices in zip(scores, indices):
            for idx, score in zip(row_indices, row_scores):
                if idx < 0:
                    continue
                item_id = self.rev_item_id_map[idx]
                agg_scores[item_id] = agg_scores.get(item_id, 0.0) + float(score)

        return list(agg_scores.items())
