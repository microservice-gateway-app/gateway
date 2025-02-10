from injector import Module, provider

from gateway.config import GatewayServiceConfigurations
from gateway.core.cache.cache_service import CacheService
from gateway.infrastructure.cache.redis_cache import RedisCache


class InfrastructureModule(Module):
    @provider
    def provide_redis_cache(self, config: GatewayServiceConfigurations) -> CacheService:
        return RedisCache(redis_url=config.CACHE_URL)
