"""
Single-file Content-Based TF-IDF + SVD Encoder

Pipeline:
    text → TF-IDF → TruncatedSVD → L2-normalized embeddings

Artifacts:
    - item_embeddings.npy
    - item_id_map.json
    - metadata.json
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple, Any

import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import normalize


# ============================================================
# Logging
# ============================================================

LOGGER = logging.getLogger(__name__)


# ============================================================
# Types
# ============================================================

ItemId = int
RowIndex = int
ItemIdMap = Dict[ItemId, RowIndex]


# ============================================================
# Configuration
# ============================================================

@dataclass(frozen=True)
class TfidfConfig:
    # Vectorizer
    max_features: int = 100_000
    min_df: int = 5
    ngram_range: Tuple[int, int] = (1, 2)
    dtype: str = "float32"

    # Columns
    item_id_col: str = "movieId"
    title_col: str = "title"
    tag_col: str = "tag"
    genre_col: str = "genres"

    # Embeddings
    embedding_dim: int = 128

    # Output
    artifact_dir: Path = Path("models/content_based")


# ============================================================
# Text preprocessing
# ============================================================

_TEXT_CLEAN_RE = re.compile(r"[^a-z0-9\s]")


def normalize_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = _TEXT_CLEAN_RE.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _ensure_pandas(df: Any) -> pd.DataFrame:
    """
    Enforce pandas boundary.
    Supports Polars via to_pandas().
    """
    if hasattr(df, "to_pandas"):
        return df.to_pandas()
    if isinstance(df, pd.DataFrame):
        return df
    raise TypeError(f"Unsupported DataFrame type: {type(df)}")


def build_item_text(
    items_df,
    tags_df,
    item_id_col: str,
    title_col: str,
    tag_col: str,
    genre_col: str,
) -> pd.DataFrame:
    """
    Build per-item normalized text:
        title + genres + aggregated tags
    """

    items_df = _ensure_pandas(items_df)
    tags_df = _ensure_pandas(tags_df)

    LOGGER.info("Aggregating tags per item")

    tags_df = tags_df[[item_id_col, tag_col]]
    tags_df[tag_col] = tags_df[tag_col].fillna("").astype(str)

    tags_agg = (
        tags_df
        .groupby(item_id_col, as_index=False)[tag_col]
        .agg(" ".join)
    )

    LOGGER.info("Preparing item text")

    df = items_df[[item_id_col, title_col, genre_col]]

    df[title_col] = df[title_col].fillna("").astype(str)
    df[genre_col] = (
        df[genre_col]
        .fillna("")
        .astype(str)
        .str.replace("|", " ", regex=False)
    )

    df = df.merge(tags_agg, on=item_id_col, how="left")
    df[tag_col] = df[tag_col].fillna("").astype(str)

    df["text"] = (
        df[title_col]
        + " "
        + df[genre_col]
        + " "
        + df[tag_col]
    ).map(normalize_text)

    out_df = df[[item_id_col, "text"]]

    LOGGER.info("Final item count: %d", len(out_df))
    return out_df


# ============================================================
# Encoder
# ============================================================

class TfidfEncoder:
    """
    Builds FAISS-ready content embeddings.

    text → TF-IDF → SVD → L2 normalize
    """

    def __init__(self, config: TfidfConfig) -> None:
        self.config = config

    def fit_transform(
        self,
        items_df: pd.DataFrame,
        tags_df: pd.DataFrame,
    ) -> Tuple[np.ndarray, ItemIdMap]:

        df = build_item_text(
            items_df=items_df,
            tags_df=tags_df,
            item_id_col=self.config.item_id_col,
            title_col=self.config.title_col,
            tag_col=self.config.tag_col,
            genre_col=self.config.genre_col,
        )

        item_ids = df[self.config.item_id_col].astype(int).tolist()
        texts = df["text"].astype(str).tolist()

        item_id_map: ItemIdMap = {
            int(item_id): idx for idx, item_id in enumerate(item_ids)
        }

        # --------------------------------------------------
        # TF-IDF
        # --------------------------------------------------
        LOGGER.info("Building TF-IDF matrix")

        vectorizer = TfidfVectorizer(
            max_features=self.config.max_features,
            min_df=self.config.min_df,
            ngram_range=self.config.ngram_range,
            dtype=np.float32,
        )

        X_tfidf: sparse.csr_matrix = vectorizer.fit_transform(texts)

        LOGGER.info(
            "TF-IDF shape=%s nnz=%d",
            X_tfidf.shape,
            X_tfidf.nnz,
        )

        # --------------------------------------------------
        # SVD
        # --------------------------------------------------
        LOGGER.info(
            "Applying TruncatedSVD (dim=%d)",
            self.config.embedding_dim,
        )

        svd = TruncatedSVD(
            n_components=self.config.embedding_dim,
            random_state=42,
        )

        X_dense = svd.fit_transform(X_tfidf).astype(np.float32)

        # --------------------------------------------------
        # Normalize
        # --------------------------------------------------
        LOGGER.info("L2-normalizing embeddings")

        X_dense = normalize(X_dense, norm="l2", axis=1)
        X_dense = np.ascontiguousarray(X_dense)

        LOGGER.info("Final embedding shape=%s", X_dense.shape)

        return X_dense, item_id_map

    def save_artifacts(
        self,
        embeddings: np.ndarray,
        item_id_map: ItemIdMap,
    ) -> None:

        out_dir = self.config.artifact_dir
        out_dir.mkdir(parents=True, exist_ok=True)

        LOGGER.info("Saving embeddings")
        np.save(out_dir / "item_embeddings.npy", embeddings)

        LOGGER.info("Saving item_id_map")
        with open(out_dir / "item_id_map.json", "w") as f:
            json.dump(item_id_map, f)

        metadata = {
            "model": "content_based_tfidf_svd",
            "num_items": int(embeddings.shape[0]),
            "embedding_dim": int(embeddings.shape[1]),
            "normalized": True,
            "dtype": "float32",
            "svd_dim": self.config.embedding_dim,
            "tfidf": {
                "max_features": self.config.max_features,
                "min_df": self.config.min_df,
                "ngram_range": self.config.ngram_range,
            },
        }

        with open(out_dir / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)

        LOGGER.info("Artifacts written to %s", out_dir)
