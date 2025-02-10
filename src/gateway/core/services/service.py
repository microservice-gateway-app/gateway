from __future__ import annotations

from base64 import b64encode
import logging
from typing import Any, Iterable

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from pydantic import BaseModel, ConfigDict, Field
import httpx


class Service(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    url: str
    health_check: str = "/health"
    openapi: str = "/openapi.json"
    auth_endpoint: str = "/auth"
    public_key: rsa.RSAPublicKey
    openapi_routes: set[str] = Field(default_factory=set)

    def encrypt_actor_id(self, actor_id: str) -> str:
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
        result = f"/{self.name}/{path}" in self.openapi_routes
        if not result:
            logging.getLogger(__name__).debug(
                f"Route /{self.name}/{path} not found on service [{self.name}], looked up among {self.openapi_routes}"
            )
        return result

    async def auth(self, actor_id: str) -> str | None:
        if not actor_id:
            return None
        response = await self.post(
            self.auth_endpoint, headers={"X-Actor-ID": self.encrypt_actor_id(actor_id)}
        )
        response_body = dict[str, str](await response.json())
        return response_body.get("access_token")

    async def request(
        self,
        method: str,
        endpoint: str,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        json: Any | None = None,
    ) -> httpx.Response:
        url = f"{self.url.rstrip('/')}/{endpoint.strip('/')}"
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method, url, headers=headers, params=params, json=json
            )
        response.raise_for_status()
        return response

    async def get(
        self,
        endpoint: str,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
    ) -> httpx.Response:
        return await self.request("GET", endpoint, headers=headers, params=params)

    async def post(
        self,
        endpoint: str,
        headers: dict[str, str] | None = None,
        json: Any | None = None,
    ) -> httpx.Response:
        return await self.request("POST", endpoint, headers=headers, json=json)

    async def put(
        self,
        endpoint: str,
        headers: dict[str, str] | None = None,
        json: Any | None = None,
    ) -> httpx.Response:
        return await self.request("PUT", endpoint, headers=headers, json=json)

    async def patch(
        self,
        endpoint: str,
        headers: dict[str, str] | None = None,
        json: Any | None = None,
    ) -> httpx.Response:
        return await self.request("PATCH", endpoint, headers=headers, json=json)

    async def delete(
        self,
        endpoint: str,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
    ) -> httpx.Response:
        return await self.request("DELETE", endpoint, headers=headers, params=params)
