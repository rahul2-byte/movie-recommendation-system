import numpy as np
import os
import asyncio
import pandas as pd
from functools import lru_cache
from typing import Optional, Dict, List
import logging

from data.loader import load_movielens_movies, load_movielens_links
from common.clients.tmdb import TMDBClient
from common.clients.imdb import IMDBClient
from configs.settings import TMDB_IMAGE_BASE, TMDB_POSTER_SIZE

log = logging.getLogger(__name__)

class MovieStore:
    def __init__(self, movies_df: pd.DataFrame, links_df: pd.DataFrame, ratings_df: Optional[pd.DataFrame] = None):
        """
        Initializes the MovieStore with movie metadata, links, and optionally ratings for popularity.
        """
        log.info("Initializing MovieStore...")
        movies = movies_df.copy()
        links = links_df.copy()

        # Extract year and process genres
        movies["year"] = movies["title"].str.extract(r"\((\d{4})\)")
        movies["genres"] = movies["genres"].fillna("").str.split("|")

        # Merge with links to get TMDB IDs
        # Avoid column collisions if movies already has tmdbId/imdbId
        cols_to_use = links.columns.difference(movies.columns).tolist() + ["movieId"]
        self.df = movies.merge(links[cols_to_use], on="movieId", how="left")
        
        # Calculate popularity if ratings are provided
        if ratings_df is not None:
            log.info("Calculating movie popularity from ratings...")
            popularity = ratings_df.groupby("movieId").size().reset_index(name="vote_count")
            self.df = self.df.merge(popularity, on="movieId", how="left")
            self.df["vote_count"] = self.df["vote_count"].fillna(0)
        else:
            self.df["vote_count"] = 0

        self.df.set_index("movieId", inplace=True)
        
        # Create a lowercase title for faster searching
        self.df["title_lower"] = self.df["title"].str.lower()
        
        self.tmdb_client = TMDBClient()
        self.imdb_client = IMDBClient()
        log.info(f"MovieStore initialized with {len(self.df)} movies.")

    # ---------------------------------------------------------
    # TMDB FETCH (CACHED)
    # ---------------------------------------------------------
    _tmdb_cache = {}


    def _sanitize_dict(self, movie_dict: dict) -> dict:
        import pandas as pd
        import numpy as np
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
            if pd.isna(val): res[field] = None
            elif val is not None:
                try: res[field] = int(val)
                except: res[field] = None
        for field in ["rating", "voteAverage", "vote_average"]:
            val = res.get(field)
            if pd.isna(val): res[field] = 0.0
            elif val is not None: res[field] = float(val)
        return res
    async def _fetch_tmdb_movie(self, tmdb_id: int) -> dict | None:
        if not tmdb_id:
            return None
        
        if tmdb_id in self._tmdb_cache:
            return self._tmdb_cache[tmdb_id]

        try:
            data = await self.tmdb_client.fetch_movie_full(tmdb_id)
            self._tmdb_cache[tmdb_id] = data
            return data
        except Exception as e:
            log.error(f"Error fetching TMDB data for {tmdb_id}: {e}")
            return None

    # ---------------------------------------------------------
    # PUBLIC API
    # ---------------------------------------------------------
    
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
            await self.tmdb_client.start()
            tmdb_data = await self._fetch_tmdb_movie(tmdb_id)
            
            if tmdb_data:
                if tmdb_data.get("poster_path"):
                    poster_url = f"{TMDB_IMAGE_BASE}/{TMDB_POSTER_SIZE}{tmdb_data['poster_path']}"
                if tmdb_data.get("backdrop_path"):
                    backdrop_url = f"{TMDB_IMAGE_BASE}/original{tmdb_data['backdrop_path']}"
                overview = tmdb_data.get("overview")
                
                # FALLBACK: If TMDB is missing key info, try IMDb (OMDb)
                if not poster_url or not overview or not backdrop_url:
                    imdb_id = tmdb_data.get("imdb_id")
                    if imdb_id:
                        await self.imdb_client.start()
                        imdb_data = await self.imdb_client.fetch_rating(imdb_id)
                        if imdb_data:
                            # Use IMDb Poster if TMDB is missing it
                            if not poster_url and imdb_data.get("Poster") != "N/A":
                                poster_url = imdb_data.get("Poster")
                            
                            # Backdrop fallback using poster if backdrop is missing
                            if not backdrop_url and poster_url:
                                backdrop_url = poster_url
                                
                            # Use IMDb Plot if TMDB overview is missing
                            imdb_plot = imdb_data.get("Plot")
                            if imdb_plot and imdb_plot != "N/A":
                                if not overview or len(overview) < 10:
                                    overview = imdb_plot
        
        return self._sanitize_dict({
            "movieId": int(movie_id),
            "tmdbId": tmdb_id,
            "title": title,
            "year": year,
            "genres": row.genres,
            "popularity": vote_count,
            "posterUrl": poster_url,
            "backdropUrl": backdrop_url,
            "overview": overview
        })


    async def search(self, query: str, limit: int = 10) -> list[dict]:
        """
        Search for movies by title with popularity-based sorting.
        """
        if not query or len(query) < 2:
            return []

        try:
            query_lower = query.lower()
            
            # 1. Exact or prefix matches (highest relevance)
            mask_prefix = self.df["title_lower"].str.startswith(query_lower, na=False)
            
            # 2. Contains matches
            mask_contains = self.df["title_lower"].str.contains(query_lower, na=False)
            
            # Combine matches
            matches = self.df[mask_contains].copy()
            
            if matches.empty:
                # Basic fuzzy matching fallback using standard difflib if needed
                # But for a real-time search, str.contains is usually preferred.
                return []

            # Add a relevance score: 2 for prefix match, 1 for contains
            matches["relevance"] = matches["title_lower"].str.startswith(query_lower).map({True: 2, False: 1})
            
            # Sort by relevance first, then by vote_count (popularity)
            matches = matches.sort_values(by=["relevance", "vote_count"], ascending=[False, False])
            
            # Take the top N
            results_df = matches.head(limit)
            
            movies = []
            for movie_id, row in results_df.iterrows():
                # For search suggestions, we return basic info immediately
                # We don't await _fetch_tmdb_movie here to keep search latency < 100ms
                
                # Sanitize fields to avoid JSON serialization errors (NaN)
                title = row["title"] if pd.notna(row["title"]) else "Unknown Title"
                
                # Handle potential name collisions from merge
                tmdb_id_col = "tmdbId" if "tmdbId" in row else ("tmdbId_x" if "tmdbId_x" in row else "tmdbId")
                tmdb_id = int(row[tmdb_id_col]) if pd.notna(row[tmdb_id_col]) else None
                
                year = int(row["year"]) if pd.notna(row["year"]) else None
                vote_count = int(row["vote_count"]) if pd.notna(row["vote_count"]) else 0
                
                poster_url = None
                if "poster_path" in row and pd.notna(row.poster_path):
                    poster_url = f"{TMDB_IMAGE_BASE}/{TMDB_POSTER_SIZE}{row.poster_path}"

                movies.append(self._sanitize_dict({
                    "movieId": int(movie_id),
                    "tmdbId": tmdb_id,
                    "title": title,
                    "year": year,
                    "genres": row.genres,
                    "popularity": vote_count,
                    "posterUrl": poster_url
                }))
                
            return movies
        except Exception as e:
            log.error(f"Error during search for '{query}': {e}")
            return []
