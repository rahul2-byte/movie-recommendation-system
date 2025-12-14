# features/build_item_features.py
"""
Item-level feature builder (FINAL – production ready)

KEPT:
- movie_rating_count
- movie_rating_mean
- movie_rating_std
- movie_age_days
- genre one-hot
- movie_year
- title TF-IDF + PCA embeddings
- tag TF-IDF + PCA embeddings

REMOVED:
- tag one-hot
- movie_last_ts
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import PCA

from .utils import (
    DF,
    downcast_numeric,
    free,
    is_gpu,
    read_parquet,
    read_csv,
    to_parquet,
)

log = logging.getLogger("features.item")


# ------------------------------------------------------------
# Helper: Extract movie title + year
# ------------------------------------------------------------
def extract_title_year(df: DF, title_col: str = "title") -> DF:
    if title_col not in df.columns:
        raise ValueError("movies metadata missing title column")

    df["movie_year"] = (
        df[title_col]
        .str.extract(r"\((\d{4})\)")
        .fillna("0")
        .astype("int32")
    )

    df["movie_title_clean"] = (
        df[title_col]
        .str.replace(r"\(\d{4}\)", "", regex=True)
        .str.lower()
        .str.strip()
    )

    return df


# ------------------------------------------------------------
# Helper: Genre one-hot (normalized)
# ------------------------------------------------------------
def parse_genres_field(
    df: DF,
    movies_col: str = "genres",
    id_col: str = "movieId",
) -> DF:
    if movies_col not in df.columns:
        raise ValueError("movies DataFrame missing genres column")

    genres = df[[id_col, movies_col]].copy()
    genres[movies_col] = genres[movies_col].fillna("none")

    genres = genres.assign(
        genre=genres[movies_col].str.split("|")
    ).explode("genre")

    genres["genre"] = (
        genres["genre"]
        .str.lower()
        .replace({"(no genres listed)": "none"})
    )

    genres["val"] = 1

    pivot = (
        genres
        .groupby([id_col, "genre"])["val"]
        .sum()
        .unstack(fill_value=0)
        .reset_index()
    )

    pivot = pivot.rename(
        columns={c: f"genre__{c}" for c in pivot.columns if c != id_col}
    )

    return pivot


# ------------------------------------------------------------
# TF-IDF + PCA builder (TITLE + TAGS)
# ------------------------------------------------------------
def build_text_embeddings(
    movies_df: DF,
    tags_path: Optional[str],
    item_col: str,
    title_dim: int = 128,
    tag_dim: int = 128,
    out_dir: Optional[str] = None,
):
    # =========================
    # TITLE EMBEDDINGS
    # =========================
    log.info("Building TITLE TF-IDF + PCA embeddings")

    tfidf_title = TfidfVectorizer(
        max_features=10_000,
        stop_words="english",
        ngram_range=(1, 2),
    )

    title_matrix = tfidf_title.fit_transform(
        movies_df["movie_title_clean"].fillna("")
    )

    pca_title = PCA(n_components=title_dim, random_state=42)
    title_embed = pca_title.fit_transform(title_matrix.toarray())

    title_df = pd.DataFrame(
        title_embed,
        columns=[f"title_pca_{i}" for i in range(title_dim)],
    )
    title_df[item_col] = movies_df[item_col].values

    if out_dir:
        to_parquet(title_df, f"{out_dir}/item_title_embeddings.parquet")

    # =========================
    # TAG EMBEDDINGS
    # =========================
    tag_df = None

    if tags_path:
        log.info("Building TAG TF-IDF + PCA embeddings")

        tags_df = (
            read_csv(tags_path)
            if tags_path.endswith(".csv")
            else read_parquet(tags_path)
        )

        tags_df["tag"] = (
            tags_df["tag"]
            .astype("string")
            .str.lower()
            .str.strip()
        )

        tag_text = (
            tags_df.groupby(item_col)["tag"]
            .apply(lambda x: " ".join([str(t) for t in x if pd.notna(t)]))
            .reset_index()
        )

        tfidf_tag = TfidfVectorizer(
            max_features=10_000,
            stop_words="english",
        )

        tag_matrix = tfidf_tag.fit_transform(tag_text["tag"].fillna(""))

        pca_tag = PCA(n_components=tag_dim, random_state=42)
        tag_embed = pca_tag.fit_transform(tag_matrix.toarray())

        tag_df = pd.DataFrame(
            tag_embed,
            columns=[f"tag_pca_{i}" for i in range(tag_dim)],
        )
        tag_df[item_col] = tag_text[item_col].values

        if out_dir:
            to_parquet(tag_df, f"{out_dir}/item_tag_embeddings.parquet")

    return title_df, tag_df


# ------------------------------------------------------------
# MAIN ITEM FEATURE BUILDER
# ------------------------------------------------------------
def build_item_features(
    interactions_path: str,
    movies_path: str,
    tags_path: Optional[str] = None,
    out_path: Optional[str] = None,
    out_dir: Optional[str] = None,
    item_col: str = "movieId",
    rating_col: str = "rating",
    time_col: str = "timestamp",
) -> DF:

    log.info("Building item features (gpu=%s)", is_gpu())

    df = read_csv(interactions_path)
    df[item_col] = df[item_col].astype("int32")
    df[rating_col] = df[rating_col].astype("float32")

    # -------------------------
    # Rating aggregates
    # -------------------------
    g = df.groupby(item_col)
    item_stats = g.agg(
        movie_rating_count=(rating_col, "count"),
        movie_rating_mean=(rating_col, "mean"),
        movie_rating_std=(rating_col, "std"),
    ).reset_index()

    # Std fix (single rating → 0)
    item_stats["movie_rating_std"] = item_stats["movie_rating_std"].fillna(0)

    # -------------------------
    # Movie age
    # -------------------------
    ts_min = int(df[time_col].min())
    first_ts = g[time_col].min().reset_index(name="movie_first_ts")

    item_stats = item_stats.merge(first_ts, on=item_col, how="left")
    item_stats["movie_age_days"] = (
        (item_stats["movie_first_ts"] - ts_min) / 86400
    ).astype("float32")

    # -------------------------
    # Movie metadata
    # -------------------------
    movies_df = (
        read_csv(movies_path)
        if movies_path.endswith(".csv")
        else read_parquet(movies_path)
    )

    movies_df = extract_title_year(movies_df)

    genre_df = parse_genres_field(movies_df)

    item_stats = item_stats.merge(
        movies_df[[item_col, "movie_year"]],
        on=item_col,
        how="left",
    )

    item_stats = item_stats.merge(
        genre_df,
        on=item_col,
        how="left",
    )

    # -------------------------
    # Text embeddings
    # -------------------------
    title_emb, tag_emb = build_text_embeddings(
        movies_df=movies_df,
        tags_path=tags_path,
        item_col=item_col,
        out_dir=out_dir,
    )

    item_stats = item_stats.merge(title_emb, on=item_col, how="left")

    if tag_emb is not None:
        item_stats = item_stats.merge(tag_emb, on=item_col, how="left")

    # -------------------------
    # FINAL CLEANUP
    # -------------------------
    # Fill embedding NaNs (movies without tags)
    emb_cols = [c for c in item_stats.columns if c.startswith(("title_pca_", "tag_pca_"))]
    item_stats[emb_cols] = item_stats[emb_cols].fillna(0)

    item_stats = downcast_numeric(item_stats)
    free(df, g)

    if out_path:
        to_parquet(item_stats, out_path)
        log.info("Saved item features → %s", out_path)

    return item_stats
