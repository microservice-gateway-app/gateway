import httpx
from fastapi import Depends, FastAPI, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from injector import Injector

from gateway.core.cache.cache_service import CacheService
from gateway.core.services.registry import ServiceRegistry

# HTTPBearer Instance
bearer_scheme = HTTPBearer()


async def get_actor_id(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> str:
    app: FastAPI = request.app
    injector: Injector = app.state.injector
    registry = injector.get(ServiceRegistry)
    cache = injector.get(CacheService)  # type: ignore

    token = credentials.credentials
    # cache hit
    if actor_id := str(await cache.get(token)):
        return actor_id

    user_service = registry.get(service="user")
    headers = dict(request.headers)
    headers.pop("content-length")
    async with httpx.AsyncClient() as client:
        user_response = await client.get(f"{user_service.url}/me", headers=headers)
    user_response.raise_for_status()
    user_data = user_response.json()
    actor_id = user_data.get("user_id", "")

    await cache.set(key=token, value=actor_id, ttl_seconds=60)

    return actor_id
