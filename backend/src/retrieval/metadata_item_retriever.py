"""
Metadata-based Item Retriever (Semantic)

- Uses movie metadata only
- Item → item similarity
- No users, no collaborative filtering
- Designed for retrieval, not ranking
"""

from pathlib import Path
from typing import List, Tuple, Dict
import json

import numpy as np
import pandas as pd
import faiss
from sentence_transformers import SentenceTransformer


ItemId = int
RowIndex = int
ItemIdMap = Dict[ItemId, RowIndex]


class MetadataItemRetriever:
    """
    Builds a semantic item-to-item retriever using movie metadata only.
    """

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        embedding_dim: int = 384,
    ) -> None:
        self.model = SentenceTransformer(model_name)
        self.embedding_dim = embedding_dim
        self.index: faiss.Index | None = None
        self.movie_ids: List[int] = []

    # --------------------------------------------------
    # OFFLINE STEP (called once)
    # --------------------------------------------------
    def build_index(
        self, movies_df: pd.DataFrame
    ) -> Tuple[np.ndarray, ItemIdMap]:
        """
        Build FAISS index and item-id mapping.

        Expected columns in movies_df:
        - movie_id (internal ID)
        - tmdb_id
        - title
        - overview
        - genres (list | str | NaN)
        - keywords (list | str | NaN)
        - top_cast (list | str | NaN)
        - director (str | NaN)
        """

        required_cols = {"movieId", "tmdb_id"}
        missing = required_cols - set(movies_df.columns)
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        texts = movies_df.apply(self._compose_text, axis=1).tolist()

        embeddings = self.model.encode(
            texts,
            batch_size=64,
            show_progress_bar=True,
            normalize_embeddings=True,
        ).astype(np.float32)

        if embeddings.shape[1] != self.embedding_dim:
            raise ValueError(
                f"Embedding dim mismatch: expected {self.embedding_dim}, "
                f"got {embeddings.shape[1]}"
            )

        self.index = faiss.IndexFlatIP(self.embedding_dim)
        self.index.add(embeddings)

        self.movie_ids = movies_df["tmdb_id"].astype(int).tolist()

        item_ids = movies_df["movieId"].astype(int).tolist()
        item_id_map: ItemIdMap = {
            item_id: idx for idx, item_id in enumerate(item_ids)
        }

        return embeddings, item_id_map

    # --------------------------------------------------
    # PERSISTENCE
    # --------------------------------------------------
    def save(
        self,
        path: Path,
        embeddings: np.ndarray,
        item_id_map: ItemIdMap,
    ) -> None:
        """
        Persist embeddings, item-id map, and metadata to disk.
        """

        path.mkdir(parents=True, exist_ok=True)

        np.save(path / "item_embeddings.npy", embeddings)

        with open(path / "item_id_map.json", "w", encoding="utf-8") as f:
            json.dump(item_id_map, f, indent=2)

        metadata = {
            "model": "metadata_item_retriever",
            "num_items": int(embeddings.shape[0]),
            "embedding_dim": int(embeddings.shape[1]),
            "normalized": True,
            "dtype": "float32",
        }

        with open(path / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

    # --------------------------------------------------
    # INTERNAL HELPERS
    # --------------------------------------------------
    @staticmethod
    def _normalize_text_list(value) -> str:
        """
        Normalize list/array/string metadata fields into a
        lowercase, space-separated string suitable for embeddings.
        """
        if value is None:
            return ""

        # numpy array or list
        if isinstance(value, (list, tuple, np.ndarray)):
            return " ".join(
                str(v).strip().lower()
                for v in value
                if isinstance(v, str) and v.strip()
            )

        # single string
        if isinstance(value, str):
            return value.strip().lower()

        return ""

    def _compose_text(self, row: pd.Series) -> str:
        """
        Compose a single text document for embedding from metadata fields.
        """

        parts = [
            self._normalize_text_list(row.get("title")),
            self._normalize_text_list(row.get("overview")),
            self._normalize_text_list(row.get("genres")),
            self._normalize_text_list(row.get("keywords")),
            self._normalize_text_list(row.get("top_cast")),
            self._normalize_text_list(row.get("director")),
        ]

        return " ".join(part for part in parts if part)
