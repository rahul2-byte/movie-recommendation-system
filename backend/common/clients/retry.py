"""
Retry utilities with exponential backoff for API calls.

Provides decorators and functions for handling transient failures.
"""

import asyncio
import random
from collections.abc import Callable
from functools import wraps
from typing import TypeVar

from aiohttp import ClientResponseError
from configs.settings import (
    INITIAL_RETRY_DELAY,
    MAX_RETRIES,
    MAX_RETRY_DELAY,
    RETRY_EXPONENTIAL_BASE,
)

from common.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")

# Exceptions that should trigger retries (transient errors)
RETRYABLE_EXCEPTIONS: tuple[type[Exception], ...] = (
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
    ClientResponseError,
)


def _is_retryable_response(error: ClientResponseError) -> bool:
    return error.status in {408, 429} or error.status >= 500


def calculate_backoff_delay(
    attempt: int,
    initial_delay: float = INITIAL_RETRY_DELAY,
    max_delay: float = MAX_RETRY_DELAY,
    exponential_base: float = RETRY_EXPONENTIAL_BASE,
) -> float:
    """
    Calculate exponential backoff delay with jitter.

    Args:
        attempt: Current attempt number (0-indexed)
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential calculation

    Returns:
        Delay in seconds with random jitter applied
    """
    exponential_delay = initial_delay * (exponential_base**attempt)
    capped_delay = min(exponential_delay, max_delay)
    jitter = random.uniform(0, capped_delay * 0.1)  # 10% jitter
    return capped_delay + jitter


async def retry_async(
    func: Callable[..., T],
    *args,
    max_retries: int = MAX_RETRIES,
    retryable_exceptions: tuple[type[Exception], ...] = RETRYABLE_EXCEPTIONS,
    **kwargs,
) -> T:
    """
    Retry an async function with exponential backoff.

    Args:
        func: Async function to retry
        *args: Positional arguments for func
        max_retries: Maximum number of retry attempts
        retryable_exceptions: Tuple of exceptions that trigger retries
        **kwargs: Keyword arguments for func

    Returns:
        Result from successful function call

    Raises:
        Last exception if all retries exhausted
    """
    last_exception = None

    for attempt in range(max_retries):
        try:
            return await func(*args, **kwargs)
        except retryable_exceptions as e:
            last_exception = e

            if isinstance(e, ClientResponseError) and not _is_retryable_response(e):
                raise

            if attempt == max_retries - 1:
                logger.error(
                    f"All {max_retries} retry attempts exhausted for {func.__name__}"
                )
                raise

            delay = calculate_backoff_delay(attempt)
            logger.warning(
                f"Attempt {attempt + 1}/{max_retries} failed for {func.__name__}: "
                f"{type(e).__name__}: {str(e)}. Retrying in {delay:.2f}s..."
            )
            await asyncio.sleep(delay)
        except Exception as e:
            # Non-retryable exception, raise immediately
            logger.error(
                f"Non-retryable exception in {func.__name__}: "
                f"{type(e).__name__}: {str(e)}"
            )
            raise

    # Should never reach here, but for type safety
    if last_exception:
        raise last_exception
    raise RuntimeError("Unexpected retry loop exit")


def retry_async_decorator(
    max_retries: int = MAX_RETRIES,
    retryable_exceptions: tuple[type[Exception], ...] = RETRYABLE_EXCEPTIONS,
):
    """
    Decorator for async functions with automatic retry logic.

    Args:
        max_retries: Maximum number of retry attempts
        retryable_exceptions: Tuple of exceptions that trigger retries

    Returns:
        Decorated function with retry capability

    Example:
        @retry_async_decorator(max_retries=3)
        async def fetch_data():
            # ... async API call
            pass
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            return await retry_async(
                func,
                *args,
                max_retries=max_retries,
                retryable_exceptions=retryable_exceptions,
                **kwargs,
            )

        return wrapper

    return decorator
