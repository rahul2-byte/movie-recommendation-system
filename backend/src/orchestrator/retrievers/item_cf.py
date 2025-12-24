import json
from pathlib import Path
from typing import Iterable, List, Tuple

import faiss
import numpy as np

from .base import BaseRetriever


class ItemCFRetriever(BaseRetriever):
    """
    Item–Item CF using ALS item embeddings.

    Query = recent item embeddings (provided at query time)
    Index = ALS item FAISS index
    """

    name = "item_cf"

    def __init__(
        self,
        model_dir: Path,
        item_embeddings: np.ndarray,
        index_path: Path,
    ) -> None:
        # -------------------------------------------------
        # Load FAISS index (built on INTERNAL item indices)
        # -------------------------------------------------
        self.index = faiss.read_index(str(index_path / "faiss.index"))

        # Item embeddings aligned with ALS internal indices
        self.item_embeddings = item_embeddings.astype(np.float32)

        # -------------------------------------------------
        # Load shared ID maps (ALS-compatible)
        # id_maps.json format:
        # {
        #   "user_id_map": {external_id: internal_idx},
        #   "item_id_map": {external_id: internal_idx}
        # }
        # -------------------------------------------------
        with open(model_dir / "id_maps.json", "r") as f:
            id_maps = json.load(f)

        # external_item_id → internal_item_index
        self.item_id_map = {
            int(ext_id): int(idx)
            for ext_id, idx in id_maps["item_id_map"].items()
        }

        # internal_item_index → external_item_id
        self.rev_item_id_map = {
            int(idx): int(ext_id)
            for ext_id, idx in id_maps["item_id_map"].items()
        }

        # -------------------------------------------------
        # Fail-fast sanity checks
        # -------------------------------------------------
        assert (
            max(self.rev_item_id_map.keys()) + 1
            == self.item_embeddings.shape[0]
        ), "Item embeddings and ID map size mismatch"

    def retrieve(
        self,
        user_id: int,
        top_k: int,
        recent_item_ids: Iterable[int] | None = None,
    ) -> List[Tuple[int, float]]:
        # -------------------------------------------------
        # Item-CF requires recent user items
        # -------------------------------------------------
        if not recent_item_ids:
            return []

        # Map external → internal indices
        seed_indices = [
            self.item_id_map[item_id]
            for item_id in recent_item_ids
            if item_id in self.item_id_map
        ]

        if not seed_indices:
            return []

        seed_vecs = self.item_embeddings[seed_indices]

        scores, indices = self.index.search(seed_vecs, top_k)

        agg_scores: dict[int, float] = {}

        for row_scores, row_indices in zip(scores, indices):
            for idx, score in zip(row_indices, row_scores):
                if idx < 0:
                    continue
                ext_item_id = self.rev_item_id_map[idx]
                agg_scores[ext_item_id] = (
                    agg_scores.get(ext_item_id, 0.0) + float(score)
                )

        return list(agg_scores.items())
