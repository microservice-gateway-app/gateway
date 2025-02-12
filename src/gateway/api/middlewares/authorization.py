import json
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from injector import Injector

from gateway.core.cache.cache_service import CacheService
from gateway.core.services.registry import ServiceRegistry

# HTTPBearer Instance
bearer_scheme = HTTPBearer(auto_error=False)


async def get_user_data(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict[str, Any]:
    app: FastAPI = request.app
    injector: Injector = app.state.injector
    registry = injector.get(ServiceRegistry)
    cache = injector.get(CacheService)  # type: ignore

    token = credentials.credentials
    # cache hit
    if user_data := await cache.get(token):
        return dict[str, Any](json.loads(str(user_data)))

    user_service = registry.get(service="users")
    headers = dict(request.headers)
    if "content-length" in headers:
        headers.pop("content-length")

    user_response = await user_service.get("/users/me", headers=headers)
    if user_response.status_code >= 400:
        raise HTTPException(status_code=user_response.status_code)
    user_data = user_response.json()

    await cache.set(key=token, value=json.dumps(user_data), ttl_seconds=60)

    return dict[str, Any](user_data)
