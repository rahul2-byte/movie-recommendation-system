"""IMDb metadata client used during offline enrichment."""

import asyncio

from configuration.settings import (
    IMDB_API_KEY,
    IMDB_BASE_URL,
    IMDB_RATE_LIMIT,
)
from observability.logging import get_logger

from infrastructure.clients.base import BaseAPIClient, ProviderRequestError

log = get_logger(__name__)


class IMDBClient(BaseAPIClient):
    """Fetch IMDb ratings without coupling enrichment to HTTP details."""

    _instance = None
    _lock = asyncio.Lock()

    def __new__(cls):
        """Return the process-local client singleton."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the client once from configured API settings."""
        if hasattr(self, "_initialized"):
            return
        super().__init__(rate_limit=IMDB_RATE_LIMIT)
        self.base_url = IMDB_BASE_URL
        self.api_key = IMDB_API_KEY
        self._initialized = True

    async def fetch_rating(self, imdb_id: str | None) -> dict:
        """Return rating data for an IMDb ID, or empty data on failure."""
        if not imdb_id:
            return {}
        params = {"apikey": self.api_key, "i": imdb_id}
        try:
            await self.start()
            response = await self._get(self.base_url, params=params)
            if response.get("Response") == "False":
                return {}
            return response
        except Exception as error:
            log.warning("IMDb rating lookup failed", imdb_id=imdb_id, error=str(error))
            raise ProviderRequestError(
                f"IMDb rating lookup failed: {imdb_id}"
            ) from error


def get_imdb_client() -> IMDBClient:
    """Return the shared IMDb client used by enrichment jobs."""
    return IMDBClient()
