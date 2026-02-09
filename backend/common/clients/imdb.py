import asyncio
from typing import Dict, Optional

from configs.settings import (
    IMDB_API_KEY,
    IMDB_BASE_URL,
    IMDB_RATE_LIMIT,
)

from common.clients.base import BaseAPIClient
from common.logger import get_logger

log = get_logger(__name__)


class IMDBClient(BaseAPIClient):
    _instance = None
    _lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(IMDBClient, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized"):
            return
        super().__init__(rate_limit=IMDB_RATE_LIMIT)
        self.base_url = IMDB_BASE_URL
        self.api_key = IMDB_API_KEY
        self._initialized = True

    async def fetch_rating(self, imdb_id: Optional[str]) -> Dict:
        if not imdb_id:
            return {}
        params = {"apikey": self.api_key, "i": imdb_id}
        try:
            await self.start()
            response = await self._get(self.base_url, params=params)
            if response.get("Response") == "False":
                return {}
            return response
        except Exception as e:
            log.error(f"IMDb Client: Error fetching {imdb_id}: {str(e)}")
            return {}


def get_imdb_client() -> IMDBClient:
    return IMDBClient()
