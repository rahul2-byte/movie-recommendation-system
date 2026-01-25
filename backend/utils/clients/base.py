"""
Base HTTP client with rate limiting and connection pooling.

Provides shared functionality for all API clients.
"""

import asyncio
from typing import Dict, Optional
from aiohttp import ClientSession, ClientTimeout, TCPConnector, ClientResponse
import time

from utils.config.settings import REQUEST_TIMEOUT, MAX_CONCURRENT_REQUESTS
from utils.logger import get_logger
from utils.clients.retry import retry_async

logger = get_logger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter for API requests.
    
    Attributes:
        rate: Maximum requests per second
        tokens: Current available tokens
        updated_at: Last token refill timestamp
    """
    
    def __init__(self, rate: int):
        """
        Initialize rate limiter.
        
        Args:
            rate: Maximum requests per second
        """
        self.rate = rate
        self.tokens = float(rate)
        self.updated_at = time.monotonic()
        self._lock = asyncio.Lock()
    
    async def acquire(self) -> None:
        """
        Acquire a token, waiting if necessary.
        
        Blocks until a token is available based on rate limit.
        """
        async with self._lock:
            while self.tokens < 1:
                await self._refill()
                if self.tokens < 1:
                    # Calculate sleep time needed
                    sleep_time = (1.0 - self.tokens) / self.rate
                    await asyncio.sleep(sleep_time)
                    await self._refill()
            
            self.tokens -= 1
    
    async def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self.updated_at
        self.tokens = min(self.rate, self.tokens + elapsed * self.rate)
        self.updated_at = now


class BaseAPIClient:
    """
    Base class for HTTP API clients with connection pooling and rate limiting.
    
    Attributes:
        session: Shared aiohttp ClientSession
        rate_limiter: Rate limiter instance
        semaphore: Concurrency control semaphore
    """
    
    def __init__(
        self,
        rate_limit: int,
        max_concurrent: int = MAX_CONCURRENT_REQUESTS,
    ):
        """
        Initialize base API client.
        
        Args:
            rate_limit: Maximum requests per second
            max_concurrent: Maximum concurrent requests
        """
        self.rate_limiter = RateLimiter(rate_limit)
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self._session: Optional[ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def start(self) -> None:
        """Initialize aiohttp session with connection pooling."""
        if self._session is None or self._session.closed:
            timeout = ClientTimeout(total=REQUEST_TIMEOUT)
            connector = TCPConnector(
                limit=MAX_CONCURRENT_REQUESTS,
                limit_per_host=MAX_CONCURRENT_REQUESTS,
                ttl_dns_cache=300,
            )
            self._session = ClientSession(
                timeout=timeout,
                connector=connector,
            )
    
    async def close(self) -> None:
        """Close aiohttp session and cleanup resources."""
        if self._session and not self._session.closed:
            await self._session.close()
            # Allow time for cleanup
            await asyncio.sleep(0.25)
    
    @property
    def session(self) -> ClientSession:
        """
        Get active session.
        
        Returns:
            Active ClientSession
            
        Raises:
            RuntimeError: If session not initialized
        """
        if self._session is None or self._session.closed:
            raise RuntimeError(
                "Session not initialized. Use 'async with' or call start()."
            )
        return self._session
    
    async def _get(
        self,
        url: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
    ) -> Dict:
        """
        Perform rate-limited GET request with retry logic.
        
        Args:
            url: Request URL
            params: Query parameters
            headers: Request headers
            
        Returns:
            JSON response as dictionary
            
        Raises:
            Exception: If request fails after all retries
        """
        async with self.semaphore:
            await self.rate_limiter.acquire()
            
            async def _request() -> Dict:
                async with self.session.get(
                    url,
                    params=params,
                    headers=headers,
                ) as response:
                    response.raise_for_status()
                    return await response.json()
            
            return await retry_async(_request)