"""
IMDb API client using OMDb API.

Provides async methods for fetching IMDb ratings and metadata.
"""

from typing import Dict, Optional

from common.clients.base import BaseAPIClient
from configs.settings import (
    IMDB_BASE_URL,
    IMDB_API_KEY,
    IMDB_RATE_LIMIT,
)
from common.logger import get_logger

logger = get_logger(__name__)


class IMDBClient(BaseAPIClient):
    """
    Async client for OMDb API (IMDb data) with rate limiting.
    
    Fetches ratings, votes, and additional metadata not available
    through TMDB.
    """
    
    def __init__(self):
        """Initialize IMDb client with appropriate rate limits."""
        super().__init__(rate_limit=IMDB_RATE_LIMIT)
        self.base_url = IMDB_BASE_URL
        self.api_key = IMDB_API_KEY
    
    async def fetch_rating(self, imdb_id: Optional[str]) -> Dict:
        """
        Fetch IMDb ratings and metadata.
        
        Args:
            imdb_id: IMDb identifier (e.g., 'tt0111161'), can be None
            
        Returns:
            Dictionary containing IMDb data:
                - imdbRating: User rating (0-10)
                - imdbVotes: Number of votes
                - Language: Primary language
                - Country: Production country
                - ... and other OMDb fields
            Returns empty dict if imdb_id is None or invalid
                
        Raises:
            ClientResponseError: If API returns error status
            asyncio.TimeoutError: If request times out
            
        Example:
            >>> async with IMDBClient() as client:
            ...     data = await client.fetch_rating('tt0111161')
            ...     print(data['imdbRating'])
        """
        if not imdb_id:
            logger.debug("No IMDb ID provided, returning empty data")
            return {}
        
        params = {
            "apikey": self.api_key,
            "i": imdb_id,
        }
        
        try:
            response = await self._get(self.base_url, params=params)
            
            # OMDb returns Response="False" for invalid IDs
            if response.get("Response") == "False":
                logger.warning(
                    f"IMDb ID {imdb_id} not found: {response.get('Error', 'Unknown error')}"
                )
                return {}
            
            logger.debug(f"Successfully fetched IMDb data for ID: {imdb_id}")
            return response
            
        except Exception as e:
            logger.error(
                f"Failed to fetch IMDb data for ID {imdb_id}: "
                f"{type(e).__name__}: {str(e)}"
            )
            # Return empty dict instead of raising to allow pipeline to continue
            return {}