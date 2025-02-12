from __future__ import annotations

from typing import Any

import httpx


class HttpClientMixin:
    base_url: str

    async def request(
        self,
        method: str,
        endpoint: str,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        json: Any | None = None,
        timeout: int = 30,
        **kwargs: Any,
    ) -> httpx.Response:
        if endpoint.startswith("http://") or endpoint.startswith("https://"):
            url = endpoint
        else:
            url = f"{self.base_url.rstrip('/')}/{endpoint.strip('/')}"
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method,
                url,
                headers=headers,
                params=params,
                json=json,
                timeout=timeout,
                **kwargs,
            )
        return response

    async def get(
        self,
        endpoint: str,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        return await self.request(
            "GET", endpoint, headers=headers, params=params, **kwargs
        )

    async def post(
        self,
        endpoint: str,
        headers: dict[str, str] | None = None,
        json: Any | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        return await self.request(
            "POST", endpoint, headers=headers, json=json, **kwargs
        )

    async def put(
        self,
        endpoint: str,
        headers: dict[str, str] | None = None,
        json: Any | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        return await self.request("PUT", endpoint, headers=headers, json=json, **kwargs)

    async def patch(
        self,
        endpoint: str,
        headers: dict[str, str] | None = None,
        json: Any | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        return await self.request(
            "PATCH", endpoint, headers=headers, json=json, **kwargs
        )

    async def delete(
        self,
        endpoint: str,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        return await self.request(
            "DELETE", endpoint, headers=headers, params=params, **kwargs
        )
