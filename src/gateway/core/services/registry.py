from __future__ import annotations

import asyncio
import logging

import httpx
from cryptography.hazmat.primitives.asymmetric import rsa

from .service import Service


class ServiceRegistry:
    def __init__(
        self,
        services: dict[str, dict[str, Service]],
        public_keys: dict[str, rsa.RSAPublicKey],
    ):
        self.services = services
        self.keys = public_keys
        self.service_health = dict[str, bool]()
        self.service_routes = dict[str, set[str]]()

    async def health_check_job(self, interval_seconds: int = 10):
        while True:
            logging.info("[heartbeat] checking service status")
            for _, versions in self.services.items():
                for version, service_version in versions.items():
                    await self.do_service_health_check(
                        service=service_version, version=version
                    )
            logging.info("[heartbeat] [DONE] checked service status")

            await asyncio.sleep(interval_seconds)

    async def do_service_health_check(self, service: Service, version: str):
        health_url = service.health_check
        openapi_url = service.openapi

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(health_url, timeout=5)
                self.service_health[f"{service.name}:{version}"] = (
                    response.status_code == 200
                )
        except Exception:
            self.service_health[f"{service.name}:{version}"] = False

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(openapi_url, timeout=5)
                if response.status_code == 200:
                    openapi_data = response.json()
                    service.add_routes(openapi_data.get("paths", {}).keys())
        except Exception:
            service.clear_routes()

    def get(self, service: str, version: str = "latest") -> Service:
        if version == "latest":
            versions = self.services[service].keys()
            latest_version = max(versions, key=lambda v: int(v.lstrip("v")))
            return self.services[service][latest_version]
        return self.services[service][version]
