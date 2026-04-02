"""Async Redis helpers for HTTP response caching."""

from __future__ import annotations

import json
import logging
from typing import Any

import redis.asyncio as redis

from app.core.config import settings

logger = logging.getLogger(__name__)

_redis: redis.Redis | None = None


async def get_redis() -> redis.Redis:
    """Singleton async Redis client (lazy)."""
    global _redis
    if _redis is None:
        _redis = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis


async def cache_get_json(key: str) -> Any | None:
    """Return deserialized JSON if present, else ``None``."""
    try:
        r = await get_redis()
        raw = await r.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception:
        logger.exception("redis get failed for key=%s", key)
        return None


async def cache_set_json(key: str, value: Any, ttl_seconds: int) -> None:
    """Serialize value to JSON and ``SETEX``."""
    try:
        r = await get_redis()
        await r.setex(key, ttl_seconds, json.dumps(value, default=str))
    except Exception:
        logger.exception("redis set failed for key=%s", key)
