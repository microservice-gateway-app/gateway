from __future__ import annotations

import logging
from typing import Any

import httpx
from fastapi import APIRouter, Body, HTTPException, Request, Security

from gateway.api.middlewares.authorization import get_user_data
from gateway.core.services.registry import ServiceRegistry


class GatewayController:
    def __init__(self, registry: ServiceRegistry):
        self.registry = registry
        self.router = APIRouter(tags=["Gateway"])
        self.logger = logging.getLogger(__name__)
        self.setup_routes()

    def setup_routes(self):
        user_service_path = "/api/{version}/users/{full_path:path}"
        other_services_path = "/api/{version}/{service_name:str}/{full_path:path}"

        self.router.get("/health")(self.health_check)

        self.router.get(user_service_path)(self.proxy_users)
        self.router.post(user_service_path)(self.proxy_users)
        self.router.put(user_service_path)(self.proxy_users)
        self.router.patch(user_service_path)(self.proxy_users)
        self.router.delete(user_service_path)(self.proxy_users)

        self.router.get(other_services_path)(self.proxy_service)
        self.router.post(other_services_path)(self.proxy_service)
        self.router.put(other_services_path)(self.proxy_service)
        self.router.patch(other_services_path)(self.proxy_service)
        self.router.delete(other_services_path)(self.proxy_service)

    async def health_check(self):
        health_status = {
            service: "UP" if status else "DOWN"
            for service, status in self.registry.service_health.items()
        }
        return {"services": health_status}

    async def proxy_users(
        self,
        request: Request,
        full_path: str,
        version: str = "v1",
        body: dict[str, Any] | None = Body(default=None),
    ):
        """
        Proxies user-related requests to the appropriate user service.

        Args:
            request (Request): The incoming HTTP request to be proxied.
            full_path (str): The full path of the user service endpoint.
            version (str, optional): The version of the user service to use. Defaults to "v1".

        Returns:
            dict: The JSON response from the user service.

        Raises:
            httpx.HTTPStatusError: If the request to the user service fails.
        """
        service = self.registry.get(service="users", version=version)
        matched_path = service.match_path(full_path)
        if matched_path is None:
            raise HTTPException(
                status_code=404, detail="Endpoint not found in service API"
            )

        headers = dict(request.headers)
        headers.pop("content-length")
        try:
            response = await service.request(
                method=request.method,
                endpoint=matched_path,
                headers=headers,
                json=body or None,
            )
            return response.json()
        except httpx.RequestError as exc:
            raise HTTPException(status_code=503, detail=f"Service unavailable: {exc}")
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=exc.response.status_code, detail=exc.response.text
            )

    async def proxy_service(
        self,
        request: Request,
        service_name: str,
        full_path: str,
        version: str = "v1",
        body: dict[str, Any] | None = Body(default=None),
        user_data: dict[str, Any] = Security(get_user_data),
    ):
        """
        Proxies a request to a specified service.

        Args:
            request (Request): The incoming HTTP request.
            service (str): The name of the service to proxy the request to.
            full_path (str): The full path of the endpoint in the service API.
            version (str, optional): The version of the service API. Defaults to "v1".

        Raises:
            HTTPException: If the service is not found in the registry.
            HTTPException: If the endpoint is not found in the service API.

        Returns:
            dict: The JSON response from the proxied service.
        """
        if service_name not in self.registry.services:
            raise HTTPException(status_code=404, detail="Service not found")
        service = self.registry.get(service=service_name, version=version)

        matched_path = service.match_path(full_path)
        if matched_path is None:
            raise HTTPException(
                status_code=404, detail="Endpoint not found in service API"
            )

        headers = dict(request.headers)
        if "content-length" in headers:
            headers.pop("content-length")
        # TODO: store and fetch access_token-user mapping to redis
        try:
            actor_id = str(user_data.get("user_id", ""))
            auth_result = await service.auth(
                actor_id=actor_id,
                scopes=list[str](user_data.get("permissions", [])),
            )
            access_token = auth_result.get("access_token")
        except httpx.RequestError as exc:
            raise HTTPException(status_code=503, detail=f"Service unavailable: {exc}")
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=exc.response.status_code, detail=exc.response.text
            )

        if access_token:
            headers = {"Authorization": f"Bearer {access_token}"}
        else:
            headers = {}

        try:
            response = await service.request(
                method=request.method,
                endpoint=matched_path,
                headers=headers,
                json=body,
                timeout=30,
            )
            return response.json()
        except httpx.RequestError as exc:
            raise HTTPException(status_code=503, detail=f"Service unavailable: {exc}")
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=exc.response.status_code, detail=exc.response.text
            )
