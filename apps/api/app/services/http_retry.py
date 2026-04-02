"""Shared HTTP retry helper."""

from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable, TypeVar

import httpx

logger = logging.getLogger(__name__)

T = TypeVar("T")

RETRY_DELAYS_SEC = (1.0, 2.0, 4.0)


async def with_http_retries(coro_factory: Callable[[], Awaitable[T]], context: str) -> T:
    """Up to 4 attempts with backoff 1s / 2s / 4s after failures."""
    last_exc: Exception | None = None
    for attempt in range(len(RETRY_DELAYS_SEC) + 1):
        try:
            return await coro_factory()
        except (httpx.HTTPError, httpx.RequestError) as exc:
            last_exc = exc
            logger.warning("%s attempt %s failed: %s", context, attempt + 1, exc)
            if attempt < len(RETRY_DELAYS_SEC):
                await asyncio.sleep(RETRY_DELAYS_SEC[attempt])
    assert last_exc is not None
    raise last_exc
