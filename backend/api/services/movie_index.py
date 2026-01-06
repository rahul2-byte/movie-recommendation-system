from pathlib import Path
from typing import List, Dict
import pandas as pd

_MOVIES_DF: pd.DataFrame | None = None

MOVIE_COLUMNS = [
    "movieId",
    "title",
    "genres",
    "year",
    "tmdbId",
]


def load_movie_index(
    movies_csv: Path,
    links_csv: Path,
) -> None:
    """
    Load and build a unified movie search index from MovieLens CSVs.

    This function MUST be called once at application startup.
    """
    global _MOVIES_DF

    # Load base movie metadata
    movies_df = pd.read_csv(movies_csv)

    # Load external IDs
    links_df = pd.read_csv(links_csv)

    # Join on movieId (LEFT JOIN — movie dataset is source of truth)
    df = movies_df.merge(
        links_df[["movieId", "tmdbId"]],
        on="movieId",
        how="left",
    )

    # Normalize / enrich
    df["title_lower"] = df["title"].str.lower()
    df["year"] = (
        df["title"]
        .str.extract(r"\((\d{4})\)")
        .astype("Int64")
    )

    # Keep only what we need in memory
    _MOVIES_DF = df[MOVIE_COLUMNS + ["title_lower"]]


def search_movies(
    query: str,
    limit: int = 10,
) -> List[Dict]:
    """
    Autocomplete-safe movie search.
    """
    if _MOVIES_DF is None:
        raise RuntimeError("Movie index not loaded")

    q = query.strip().lower()
    if len(q) < 2:
        return []

    matches = (
        _MOVIES_DF[
            _MOVIES_DF["title_lower"].str.contains(q, na=False)
        ]
        .head(limit)
    )

    return [
        {
            "movie_id": int(row.movieId),
            "title": row.title,
            "year": int(row.year) if pd.notna(row.year) else None,
            "genres": row.genres.split("|") if isinstance(row.genres, str) else [],
            "tmdb_id": int(row.tmdbId) if pd.notna(row.tmdbId) else None,
        }
        for _, row in matches.iterrows()
    ]
