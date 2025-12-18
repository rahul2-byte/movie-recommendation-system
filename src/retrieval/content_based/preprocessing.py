import logging
import re
from typing import Any

import pandas as pd

LOGGER = logging.getLogger(__name__)

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
    Ensure input is a pandas DataFrame.
    Converts from Polars if needed.
    """
    # Polars DataFrame has to_pandas()
    if hasattr(df, "to_pandas"):
        return df.to_pandas()
    # Pandas DataFrame
    if isinstance(df, pd.DataFrame):
        return df
    raise TypeError(f"Unsupported DataFrame type: {type(df)}")


def build_item_text(
    items_df,
    tags_df,
    item_id_col: str,
    title_col: str,
    tag_col: str,
    genre_col: str = "genres",
) -> pd.DataFrame:
    """
    Build per-item text by combining:
        - title
        - genres ("Comedy|Drama" → "Comedy Drama")
        - aggregated tags

    ALWAYS returns a pandas DataFrame.
    """

    # -------------------------------------------------
    # Enforce pandas boundary (CRITICAL)
    # -------------------------------------------------
    items_df = _ensure_pandas(items_df)
    tags_df = _ensure_pandas(tags_df)

    LOGGER.info("Aggregating tags per item")

    # -----------------------------
    # Aggregate tags
    # -----------------------------
    tags_df = tags_df[[item_id_col, tag_col]]
    tags_df[tag_col] = tags_df[tag_col].fillna("").astype(str)

    tags_agg = (
        tags_df
        .groupby(item_id_col, as_index=False)[tag_col]
        .agg(" ".join)
    )

    LOGGER.info("Preparing items dataframe")

    # -----------------------------
    # Prepare items
    # -----------------------------
    df = items_df[[item_id_col, title_col, genre_col]]

    df[title_col] = df[title_col].fillna("").astype(str)
    df[genre_col] = (
        df[genre_col]
        .fillna("")
        .astype(str)
        .str.replace("|", " ", regex=False)
    )

    # -----------------------------
    # Join tags
    # -----------------------------
    df = df.merge(tags_agg, on=item_id_col, how="left")
    df[tag_col] = df[tag_col].fillna("").astype(str)

    # -----------------------------
    # Concatenate + normalize
    # -----------------------------
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
