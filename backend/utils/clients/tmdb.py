"""
TMDB (The Movie Database) API client.

Provides async methods for fetching movie data from TMDB API.
"""

from typing import Dict

from utils.clients.base import BaseAPIClient
from utils.config.settings import (
    TMDB_BASE_URL,
    TMDB_ACCESS_TOKEN,
    TMDB_RATE_LIMIT,
)
from utils.logger import get_logger

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
        """
        Fetch complete movie data in a single API call.
        
        Uses append_to_response to fetch movie details, keywords,
        and credits in one request instead of three separate calls.
        
        Args:
            tmdb_id: TMDB movie identifier
            
        Returns:
            Dictionary containing:
                - Movie details (title, overview, runtime, etc.)
                - Keywords (nested under 'keywords' key)
                - Credits (nested under 'credits' key)
                
        Raises:
            ClientResponseError: If API returns error status
            asyncio.TimeoutError: If request times out
            
        Example:
            >>> async with TMDBClient() as client:
            ...     data = await client.fetch_movie_full(550)
            ...     print(data['title'])
            ...     print(data['keywords']['keywords'])
            ...     print(data['credits']['cast'])
        """
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