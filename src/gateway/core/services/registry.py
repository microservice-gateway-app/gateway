from __future__ import annotations

import asyncio
import logging

from cryptography.hazmat.primitives.asymmetric import rsa

from .service import Service

ServiceName = str
Version = str
ServiceRoutes = set[str]
ServiceStatus = bool


class ServiceRegistry:
    def __init__(
        self,
        services: dict[ServiceName, dict[Version, Service]],
        public_keys: dict[str, rsa.RSAPublicKey],
    ):
        self.services = services
        self.keys = public_keys
        self.service_health = dict[ServiceName, ServiceStatus]()
        self.service_routes = dict[ServiceName, ServiceRoutes]()
        self.logger = logging.getLogger(__name__)

    async def health_check_job(self, interval_seconds: int = 30) -> None:
        while True:
            self.logger.info("checking service status")
            for _, versions in self.services.items():
                for version, service_version in versions.items():
                    await self.do_service_health_check(
                        service=service_version, version=version
                    )
            self.logger.info("[DONE] checked service status")

            await asyncio.sleep(interval_seconds)

    async def do_service_health_check(self, service: Service, version: str):
        try:
            response = await service.do_health_check(timeout=1)
            self.service_health[f"{service.name}:{version}"] = (
                response.status_code == 200
            )
        except Exception:
            self.service_health[f"{service.name}:{version}"] = False

        try:
            response = await service.fetch_openapi_definitions(timeout=5)
            if response.status_code == 200:
                openapi_data = response.json()
                service.clear_routes()
                service.add_routes(openapi_data.get("paths", {}).keys())
        except Exception:
            service.clear_routes()

    def get(self, service: str, version: str = "latest") -> Service:
        if version == "latest":
            versions = self.services[service].keys()
            latest_version = max(versions, key=lambda v: int(v.lstrip("v")))
            return self.services[service][latest_version]
        return self.services[service][version]
