import json
import logging
from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import normalize

from .config import TfidfConfig
from .types import ItemIdMap
from .preprocessing import build_item_text

LOGGER = logging.getLogger(__name__)


class TfidfEncoder:
    """
    Builds FAISS-ready content-based item embeddings.

    Pipeline:
        text → TF-IDF → TruncatedSVD → L2-normalized dense embeddings
    """

    def __init__(self, config: TfidfConfig) -> None:
        self.config = config

    def fit_transform(
        self,
        items_df: pd.DataFrame,
        tags_df: pd.DataFrame,
    ) -> Tuple[np.ndarray, ItemIdMap]:
        """
        Build dense, normalized content embeddings.

        Returns:
            embeddings: np.ndarray of shape (num_items, emb_dim)
            item_id_map: {original_item_id: row_index}
        """

        # -------------------------------------------------
        # Build text corpus
        # -------------------------------------------------
        df = build_item_text(
            items_df=items_df,
            tags_df=tags_df,
            item_id_col=self.config.item_id_col,
            title_col=self.config.title_col,
            tag_col=self.config.tag_col,
        )

        item_ids = df[self.config.item_id_col].astype(int).tolist()
        texts = df["text"].astype(str).tolist()

        item_id_map: ItemIdMap = {
            int(item_id): idx for idx, item_id in enumerate(item_ids)
        }

        # -------------------------------------------------
        # TF-IDF (sparse)
        # -------------------------------------------------
        LOGGER.info("Building TF-IDF matrix")

        vectorizer = TfidfVectorizer(
            max_features=self.config.max_features,
            min_df=self.config.min_df,
            ngram_range=self.config.ngram_range,
            dtype=np.float32,
        )

        X_tfidf: sparse.csr_matrix = vectorizer.fit_transform(texts)

        LOGGER.info(
            "TF-IDF matrix shape=%s nnz=%d",
            X_tfidf.shape,
            X_tfidf.nnz,
        )

        # -------------------------------------------------
        # SVD → dense embeddings
        # -------------------------------------------------
        LOGGER.info(
            "Applying TruncatedSVD (dim=%d)",
            self.config.embedding_dim,
        )

        svd = TruncatedSVD(
            n_components=self.config.embedding_dim,
            random_state=42,
        )

        X_dense = svd.fit_transform(X_tfidf).astype(np.float32)

        # -------------------------------------------------
        # L2 normalization (cosine space)
        # -------------------------------------------------
        LOGGER.info("L2-normalizing embeddings")

        X_dense = normalize(X_dense, norm="l2", axis=1)
        X_dense = np.ascontiguousarray(X_dense)

        LOGGER.info(
            "Final embeddings shape=%s",
            X_dense.shape,
        )

        return X_dense, item_id_map

    def save_artifacts(
        self,
        embeddings: np.ndarray,
        item_id_map: ItemIdMap,
    ) -> None:
        """
        Persist FAISS-ready artifacts.
        """
        out_dir: Path = self.config.artifact_dir
        out_dir.mkdir(parents=True, exist_ok=True)

        # -------------------------------------------------
        # Save embeddings
        # -------------------------------------------------
        LOGGER.info("Saving item embeddings")

        np.save(out_dir / "item_embeddings.npy", embeddings)

        # -------------------------------------------------
        # Save item_id_map
        # -------------------------------------------------
        LOGGER.info("Saving item_id_map")

        with open(out_dir / "item_id_map.json", "w") as f:
            json.dump(item_id_map, f)

        # -------------------------------------------------
        # Save metadata
        # -------------------------------------------------
        metadata = {
            "model": "content_based_tfidf_svd",
            "num_items": int(embeddings.shape[0]),
            "embedding_dim": int(embeddings.shape[1]),
            "normalized": True,
            "dtype": "float32",
            "svd_dim": int(self.config.embedding_dim),
            "tfidf": {
                "max_features": self.config.max_features,
                "min_df": self.config.min_df,
                "ngram_range": self.config.ngram_range,
            },
        }

        with open(out_dir / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)

        LOGGER.info("Content-based artifacts written to %s", out_dir)
