from __future__ import annotations

import json
from functools import lru_cache

import redis.asyncio as redis

from app.core.config import settings


@lru_cache
def get_redis_client() -> redis.Redis:
    return redis.from_url(settings.redis_url, decode_responses=True)


async def enqueue_job(job_id: str) -> None:
    client = get_redis_client()
    payload = json.dumps({"job_id": job_id})
    await client.lpush(settings.redis_job_queue_key, payload)


async def close_redis() -> None:
    client = get_redis_client()
    await client.aclose()
    get_redis_client.cache_clear()
