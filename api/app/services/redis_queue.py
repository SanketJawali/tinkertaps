from __future__ import annotations

import json
from functools import lru_cache

import redis.asyncio as redis
from fastapi import status
from redis.exceptions import RedisError

from app.core.config import settings
from app.core.errors import ErrorCode, raise_api_error
from app.core.logging import get_logger

logger = get_logger(__name__)


@lru_cache
def get_redis_client() -> redis.Redis:
    return redis.from_url(settings.redis_url, decode_responses=True)


async def enqueue_job(job_id: str) -> None:
    try:
        client = get_redis_client()
        payload = json.dumps({"job_id": job_id})
        await client.lpush(settings.redis_job_queue_key, payload)
    except RedisError as exc:
        raise_api_error(
            code=ErrorCode.QUEUE_UNAVAILABLE,
            message="Failed to enqueue job for processing",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            logger=logger,
            log_message="Redis enqueue failed",
            exc=exc,
            job_id=job_id,
        )


async def close_redis() -> None:
    client = get_redis_client()
    await client.aclose()
    get_redis_client.cache_clear()
