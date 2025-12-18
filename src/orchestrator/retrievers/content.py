import json
from pathlib import Path
from typing import List, Tuple

import faiss
import numpy as np

from .base import BaseRetriever


class ContentBasedRetriever(BaseRetriever):
    """
    FAISS-backed content-based retriever.
    Uses cosine similarity over TF-IDF+SVD embeddings.
    """

    name = "content"

    def __init__(
        self, 
        model_dir: Path,
        index_path: Path
        ) -> None:
        self.model_dir = model_dir

        self.index = faiss.read_index(str(index_path / "faiss.index"))
        self.item_id_map = json.load(
            open(model_dir / "item_id_map.json", "r")
        )
        self.rev_map = {v: k for k, v in self.item_id_map.items()}

        # For cold-start we use centroid embedding
        self.item_embeddings = np.load(
            model_dir / "item_embeddings.npy"
        )
        self.centroid = (
            self.item_embeddings.mean(axis=0, keepdims=True)
            .astype(np.float32)
        )

    def retrieve(
        self,
        user_id: int,
        top_k: int,
    ) -> List[Tuple[int, float]]:
        scores, indices = self.index.search(self.centroid, top_k)

        results: List[Tuple[int, float]] = []
        for idx, score in zip(indices[0], scores[0]):
            if idx < 0:
                continue
            item_id = int(self.rev_map[idx])
            results.append((item_id, float(score)))

        return results
