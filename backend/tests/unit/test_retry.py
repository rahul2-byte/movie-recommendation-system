import asyncio

import pytest
from aiohttp import ClientResponseError, RequestInfo
from infrastructure.clients.retry import retry_async
from multidict import CIMultiDict
from yarl import URL


def test_retry_async_does_not_retry_unauthorized_responses():
    attempts = 0

    async def request():
        nonlocal attempts
        attempts += 1
        raise ClientResponseError(
            RequestInfo(
                URL("https://example.test"),
                "GET",
                CIMultiDict(),
                URL("https://example.test"),
            ),
            (),
            status=401,
        )

    with pytest.raises(ClientResponseError):
        asyncio.run(retry_async(request, max_retries=5))

    assert attempts == 1
