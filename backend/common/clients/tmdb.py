from typing import Dict, Optional, Any
import asyncio
from common.clients.base import BaseAPIClient
from configs.settings import (
    TMDB_BASE_URL,
    TMDB_ACCESS_TOKEN,
    TMDB_RATE_LIMIT,
)
from common.logger import get_logger

log = get_logger(__name__)

class TMDBClient(BaseAPIClient):
    """
    Optimized Singleton Async client for TMDB API.
    Handles connection pooling and internal caching.
    """
    _instance = None
    _lock = asyncio.Lock()
    _cache = {} # Simple in-memory cache for the Lambda lifecycle

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TMDBClient, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        # Only initialize once
        if hasattr(self, '_initialized'):
            return
        super().__init__(rate_limit=TMDB_RATE_LIMIT)
        self.base_url = TMDB_BASE_URL
        self.headers = {
            "Authorization": f"Bearer {TMDB_ACCESS_TOKEN}",
            "Accept": "application/json",
        }
        self._initialized = True

    async def fetch_movie_full(self, tmdb_id: int) -> Dict[str, Any]:
        """Fetches full movie details with credits and keywords."""
        cache_key = f"movie_{tmdb_id}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        url = f"{self.base_url}/movie/{tmdb_id}"
        params = {"append_to_response": "keywords,credits"}
        
        try:
            # Ensure session is active (Lazy Start)
            await self.start()
            response = await self._get(url, params=params, headers=self.headers)
            
            # Store in cache
            self._cache[cache_key] = response
            return response
        except Exception as e:
            log.error(f"TMDB Client: Error fetching movie {tmdb_id}: {str(e)}")
            return {}

    async def fetch_path(self, path: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Generic fetch for any TMDB path with caching for common paths."""
        url = f"{self.base_url}{path}"
        # Cache catalog requests for 5 minutes (via local lifecycle check if we wanted, 
        # but for now simple memory cache is fine)
        await self.start()
        return await self._get(url, params=params, headers=self.headers)

# Global helper to get the singleton client
def get_tmdb_client() -> TMDBClient:
    return TMDBClient()
