"""
TMDB (The Movie Database) API client.

Provides async methods for fetching movie data from TMDB API.
"""

from typing import Dict

from common.clients.base import BaseAPIClient
from configs.settings import (
    TMDB_BASE_URL,
    TMDB_ACCESS_TOKEN,
    TMDB_RATE_LIMIT,
)
from common.logger import get_logger

logger = get_logger(__name__)


class TMDBClient(BaseAPIClient):
    """
    Async client for TMDB API with rate limiting and retry logic.
    
    Uses Bearer token authentication and optimized append_to_response
    to minimize API calls.
    """
    
    def __init__(self):
        """Initialize TMDB client with appropriate rate limits."""
        super().__init__(rate_limit=TMDB_RATE_LIMIT)
        self.base_url = TMDB_BASE_URL
        self.headers = {
            "Authorization": f"Bearer {TMDB_ACCESS_TOKEN}",
            "Accept": "application/json",
        }
    
    async def fetch_movie_full(self, tmdb_id: int) -> Dict:
        # ... (rest of the code)
        url = f"{self.base_url}/movie/{tmdb_id}"
        params = {
            "append_to_response": "keywords,credits"
        }
        
        try:
            response = await self._get(url, params=params, headers=self.headers)
            logger.debug(f"Successfully fetched TMDB data for movie ID: {tmdb_id}")
            return response
        except Exception as e:
            logger.error(
                f"Failed to fetch TMDB data for movie ID {tmdb_id}: "
                f"{type(e).__name__}: {str(e)}"
            )
            raise

    async def fetch_path(self, path: str, params: Dict = None) -> Dict:
        """
        Generic fetch for any TMDB API path.
        
        Args:
            path: API path starting with / (e.g. /movie/popular)
            params: Query parameters
            
        Returns:
            JSON response dictionary
        """
        url = f"{self.base_url}{path}"
        return await self._get(url, params=params, headers=self.headers)