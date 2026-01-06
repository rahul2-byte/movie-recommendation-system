from pathlib import Path
import os
import requests
import pandas as pd
from functools import lru_cache


TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p"
TMDB_POSTER_SIZE = "w342"

TMDB_TOKEN = os.getenv("TMDB_ACCESS_TOKEN")

if not TMDB_TOKEN:
    raise RuntimeError("TMDB_ACCESS_TOKEN not set")


class MovieStore:
    def __init__(self, movies_csv: Path, links_csv: Path):
        movies = pd.read_csv(movies_csv)
        links = pd.read_csv(links_csv)

        movies["year"] = movies["title"].str.extract(r"\((\d{4})\)")
        movies["genres"] = movies["genres"].fillna("").str.split("|")

        self.df = movies.merge(links, on="movieId", how="left")
        self.df.set_index("movieId", inplace=True)

        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {TMDB_TOKEN}",
            "Accept": "application/json",
        })

    # ---------------------------------------------------------
    # TMDB FETCH (CACHED)
    # ---------------------------------------------------------
    @lru_cache(maxsize=20_000)
    def _fetch_tmdb_movie(self, tmdb_id: int) -> dict | None:
        if not tmdb_id:
            return None

        try:
            resp = self._session.get(
                f"{TMDB_BASE_URL}/movie/{tmdb_id}",
                timeout=6,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception:
            return None

    # ---------------------------------------------------------
    # PUBLIC API
    # ---------------------------------------------------------
    def get(self, movie_id: int) -> dict | None:
        if movie_id not in self.df.index:
            return None

        row = self.df.loc[movie_id]

        tmdb_id = int(row.tmdbId) if pd.notna(row.tmdbId) else None
        tmdb_data = self._fetch_tmdb_movie(tmdb_id) if tmdb_id else None

        poster_path = tmdb_data.get("poster_path") if tmdb_data else None

        return {
            "movieId": int(movie_id),
            "tmdbId": tmdb_id,
            "title": row.title,
            "year": (
                int(row.year)
                if pd.notna(row.year)
                else int(tmdb_data["release_date"][:4])
                if tmdb_data and tmdb_data.get("release_date")
                else None
            ),
            "genres": row.genres,
            "rating": tmdb_data.get("vote_average") if tmdb_data else None,
            "overview": tmdb_data.get("overview") if tmdb_data else None,
            "posterUrl": (
                f"{TMDB_IMAGE_BASE}/{TMDB_POSTER_SIZE}{poster_path}"
                if poster_path
                else None
            ),
        }
