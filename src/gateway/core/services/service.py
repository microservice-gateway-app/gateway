from __future__ import annotations

from base64 import b64encode
from typing import Any, Iterable, Self
from urllib.parse import urlparse

import httpx
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .auth import AuthContext
from .client import HttpClientMixin


def match_route(route: str, path: str) -> bool:
    route_parts = route.strip("/").split("/")
    path_parts = path.strip("/").split("/")
    if len(route_parts) != len(path_parts):
        return False
    for route_part, path_part in zip(route_parts, path_parts):
        if route_part.startswith("{") and route_part.endswith("}"):
            continue
        if route_part != path_part:
            return False
    return True


class Service(BaseModel, HttpClientMixin):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    base_url: str
    health_check_path: str = "/health"
    openapi_path: str = "/openapi.json"
    public_key: rsa.RSAPublicKey
    openapi_routes: set[str] = Field(default_factory=set)
    auth_context: AuthContext | None = Field(alias="auth")

    @model_validator(mode="after")
    def after_init(self) -> Self:
        if self.auth_context:
            self.auth_context.public_key = self.public_key
            self.auth_context.base_url = self.base_url
        return self

    def _encrypt_actor_id(self, actor_id: str) -> str:
        encrypted = self.public_key.encrypt(
            actor_id.encode(),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        return b64encode(encrypted).decode()

    def add_routes(self, paths: Iterable[str]) -> None:
        self.openapi_routes.update(paths)

    def clear_routes(self) -> None:
        self.openapi_routes.clear()

    def has_route(self, path: str) -> bool:
        parsed_path = urlparse(path).path
        return any(match_route(route, parsed_path) for route in self.openapi_routes)

    def match_path(self, path: str) -> str | None:
        possible_paths = [f"/{path}", f"/{self.name}/{path}"]
        for path in possible_paths:
            if self.has_route(path=path):
                return path.lstrip("/")
        return None

    async def auth(self, **kwargs: Any) -> dict[str, str]:
        if not self.auth_context:
            return {}
        return await self.auth_context.auth(**kwargs) or {}

    async def do_health_check(self, timeout: int = 1) -> httpx.Response:
        return await self.get(self.health_check_path, timeout=timeout)

    async def fetch_openapi_definitions(self, timeout: int = 5) -> httpx.Response:
        return await self.get(self.openapi_path, timeout=timeout)
