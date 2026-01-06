from pathlib import Path
import pandas as pd

_MOVIES = None


def load_movies(csv_path: Path):
    global _MOVIES
    df = pd.read_csv(csv_path)

    df["year"] = df["title"].str.extract(r"\((\d{4})\)").astype("Int64")
    df["genres"] = df["genres"].fillna("").apply(lambda x: x.split("|"))

    _MOVIES = df.set_index("movieId")


def get_movie(movie_id: int) -> dict | None:
    if _MOVIES is None:
        raise RuntimeError("Movies not loaded")

    if movie_id not in _MOVIES.index:
        return None

    row = _MOVIES.loc[movie_id]
    return {
        "movie_id": movie_id,
        "title": row["title"],
        "year": int(row["year"]) if pd.notna(row["year"]) else None,
        "genres": row["genres"],
    }
