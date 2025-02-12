from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from injector import Injector, Module, provider, singleton

from gateway.api.controllers.gateway_controller import GatewayController
from gateway.core.services.registry import ServiceRegistry


class GatewayApp:
    def __init__(
        self,
        service_registry: ServiceRegistry,
    ):
        self.registry = service_registry
        self.controller = GatewayController(self.registry)
        self.app: FastAPI = FastAPI(title="Gateway", lifespan=self.startup_event)
        self.app.include_router(self.controller.router)

    @asynccontextmanager
    async def startup_event(self, _: FastAPI):
        task = asyncio.create_task(self.registry.health_check_job())
        yield
        task.cancel()


class APIModule(Module):
    @singleton
    @provider
    def provide_app(
        self,
        service_registry: ServiceRegistry,
        injector: Injector,
    ) -> GatewayApp:
        app = GatewayApp(service_registry=service_registry)
        app.app.state.injector = injector
        return app
