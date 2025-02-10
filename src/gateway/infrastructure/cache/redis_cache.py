from datetime import UTC, datetime
from typing import Any

from redis.asyncio import Redis

from gateway.core.cache.cache_service import CacheService


class RedisCache(CacheService):
    def __init__(self, redis_url: str):
        self.redis = Redis.from_url(redis_url)  # type: ignore

    async def get(self, key: str) -> Any | None:
        value = await self.redis.get(key)
        if value is None:
            return None
        return value.decode("utf-8")

    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int | None = None,
        expires_at: datetime | None = None,
    ) -> None:
        if expires_at:
            await self.redis.set(key, value, exat=expires_at.astimezone(UTC))
        elif ttl_seconds:
            await self.redis.set(key, value, ex=ttl_seconds)
        else:
            await self.redis.set(key, value)
