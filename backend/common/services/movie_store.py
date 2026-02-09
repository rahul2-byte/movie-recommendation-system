import asyncio
import logging
import os
from functools import lru_cache
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from configs.settings import TMDB_IMAGE_BASE, TMDB_POSTER_SIZE
from data.loader import load_movielens_links, load_movielens_movies

from common.clients.imdb import get_imdb_client
from common.clients.tmdb import get_tmdb_client

log = logging.getLogger(__name__)


class MovieStore:
    def __init__(
        self,
        movies_df: pd.DataFrame,
        links_df: pd.DataFrame,
        ratings_df: Optional[pd.DataFrame] = None,
    ):
        log.info("Initializing MovieStore...")
        movies = movies_df.copy()
        links = links_df.copy()
        movies["year"] = movies["title"].str.extract(r"\((\d{4})\)")
        movies["genres"] = movies["genres"].fillna("").str.split("|")
        cols_to_use = links.columns.difference(movies.columns).tolist() + ["movieId"]
        self.df = movies.merge(links[cols_to_use], on="movieId", how="left")
        if ratings_df is not None:
            popularity = (
                ratings_df.groupby("movieId").size().reset_index(name="vote_count")
            )
            self.df = self.df.merge(popularity, on="movieId", how="left")
            self.df["vote_count"] = self.df["vote_count"].fillna(0)
        else:
            self.df["vote_count"] = 0
        self.df.set_index("movieId", inplace=True)
        self.df["title_lower"] = self.df["title"].str.lower()
        self.tmdb_client = get_tmdb_client()
        self.imdb_client = get_imdb_client()
        log.info(f"MovieStore initialized with {len(self.df)} movies.")

    def _sanitize_dict(self, movie_dict: dict) -> dict:
        import numpy as np
        import pandas as pd

        res = movie_dict.copy()
        genres = res.get("genres")
        if pd.isna(genres) if not isinstance(genres, (list, np.ndarray)) else False:
            res["genres"] = []
        elif isinstance(genres, str):
            res["genres"] = genres.split("|")
        elif isinstance(genres, (list, np.ndarray)):
            res["genres"] = [str(g) for g in genres if pd.notna(g)]
        else:
            res["genres"] = []
        for field in ["year", "popularity", "vote_count", "tmdbId", "movieId"]:
            val = res.get(field)
            if pd.isna(val):
                res[field] = None
            elif val is not None:
                try:
                    res[field] = int(val)
                except:
                    res[field] = None
        for field in ["rating", "voteAverage", "vote_average"]:
            val = res.get(field)
            if pd.isna(val):
                res[field] = 0.0
            elif val is not None:
                res[field] = float(val)
        return res

    async def get(self, movie_id: int) -> dict | None:
        if movie_id not in self.df.index:
            return None
        row = self.df.loc[movie_id]
        tmdb_id = int(row.tmdbId) if pd.notna(row.tmdbId) else None
        title = row.title if pd.notna(row.title) else "Unknown Title"
        year = int(row.year) if pd.notna(row.year) else None
        vote_count = int(row.vote_count) if pd.notna(row.vote_count) else 0
        poster_url = None
        backdrop_url = None
        overview = None
        if tmdb_id:
            tmdb_data = await self.tmdb_client.fetch_movie_full(tmdb_id)
            if tmdb_data:
                if tmdb_data.get("poster_path"):
                    poster_url = f"{TMDB_IMAGE_BASE}/{TMDB_POSTER_SIZE}{tmdb_data['poster_path']}"
                if tmdb_data.get("backdrop_path"):
                    backdrop_url = (
                        f"{TMDB_IMAGE_BASE}/original{tmdb_data['backdrop_path']}"
                    )
                overview = tmdb_data.get("overview")
                if not poster_url or not overview or not backdrop_url:
                    imdb_id = tmdb_data.get("imdb_id")
                    if imdb_id:
                        imdb_data = await self.imdb_client.fetch_rating(imdb_id)
                        if imdb_data:
                            if not poster_url and imdb_data.get("Poster") != "N/A":
                                poster_url = imdb_data.get("Poster")
                            if not backdrop_url and poster_url:
                                backdrop_url = poster_url
                            imdb_plot = imdb_data.get("Plot")
                            if imdb_plot and imdb_plot != "N/A":
                                if not overview or len(overview) < 10:
                                    overview = imdb_plot
        return self._sanitize_dict(
            {
                "movieId": int(movie_id),
                "tmdbId": tmdb_id,
                "title": title,
                "year": year,
                "genres": row.genres,
                "popularity": vote_count,
                "posterUrl": poster_url,
                "backdropUrl": backdrop_url,
                "overview": overview,
            }
        )

    async def search(self, query: str, limit: int = 10) -> list[dict]:
        if not query or len(query) < 2:
            return []
        try:
            query_lower = query.lower()
            mask_contains = self.df["title_lower"].str.contains(query_lower, na=False)
            matches = self.df[mask_contains].copy()
            if matches.empty:
                return []
            matches["relevance"] = (
                matches["title_lower"]
                .str.startswith(query_lower)
                .map({True: 2, False: 1})
            )
            matches = matches.sort_values(
                by=["relevance", "vote_count"], ascending=[False, False]
            )
            results_df = matches.head(limit)
            movies = []
            for movie_id, row in results_df.iterrows():
                tmdb_id_col = (
                    "tmdbId"
                    if "tmdbId" in row
                    else ("tmdbId_x" if "tmdbId_x" in row else "tmdbId")
                )
                tmdb_id = int(row[tmdb_id_col]) if pd.notna(row[tmdb_id_col]) else None
                poster_url = None
                if "poster_path" in row and pd.notna(row.poster_path):
                    poster_url = (
                        f"{TMDB_IMAGE_BASE}/{TMDB_POSTER_SIZE}{row.poster_path}"
                    )
                movies.append(
                    self._sanitize_dict(
                        {
                            "movieId": int(movie_id),
                            "tmdbId": tmdb_id,
                            "title": row["title"],
                            "year": int(row["year"]) if pd.notna(row["year"]) else None,
                            "genres": row.genres,
                            "popularity": int(row["vote_count"]),
                            "posterUrl": poster_url,
                        }
                    )
                )
            return movies
        except Exception as e:
            log.error(f'Error during search for "{query}": {e}')
            return []
