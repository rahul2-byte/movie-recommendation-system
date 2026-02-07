import os
import asyncio
import pandas as pd
from functools import lru_cache
from typing import Optional, Dict, List
import logging

from data.loader import load_movielens_movies, load_movielens_links
from common.clients.tmdb import TMDBClient
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
        self.df = movies.merge(links, on="movieId", how="left")
        
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
        log.info(f"MovieStore initialized with {len(self.df)} movies.")

    # ---------------------------------------------------------
    # TMDB FETCH (CACHED)
    # ---------------------------------------------------------
    _tmdb_cache = {}

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
        overview = None
        if tmdb_id:
            # Note: The caller (Pipeline) should ideally manage the TMDB session 
            # if calling many 'get' in parallel, or we ensure 'start' is called once.
            # To be safe for parallel usage within this instance:
            await self.tmdb_client.start()
            tmdb_data = await self._fetch_tmdb_movie(tmdb_id)
            if tmdb_data:
                if "poster_path" in tmdb_data and tmdb_data["poster_path"]:
                    poster_url = f"{TMDB_IMAGE_BASE}/{TMDB_POSTER_SIZE}{tmdb_data['poster_path']}"
                if "overview" in tmdb_data:
                    overview = tmdb_data["overview"]
        
        return {
            "movieId": int(movie_id),
            "tmdbId": tmdb_id,
            "title": title,
            "year": year,
            "genres": row.genres,
            "popularity": vote_count,
            "posterUrl": poster_url,
            "overview": overview
        }

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
                title = row.title if pd.notna(row.title) else "Unknown Title"
                tmdb_id = int(row.tmdbId) if pd.notna(row.tmdbId) else None
                year = int(row.year) if pd.notna(row.year) else None
                vote_count = int(row.vote_count) if pd.notna(row.vote_count) else 0

                movies.append({
                    "movieId": int(movie_id),
                    "tmdbId": tmdb_id,
                    "title": title,
                    "year": year,
                    "genres": row.genres,
                    "popularity": vote_count
                })
                
            return movies
        except Exception as e:
            log.error(f"Error during search for '{query}': {e}")
            return []
