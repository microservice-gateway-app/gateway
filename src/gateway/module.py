from functools import lru_cache

from fastapi import FastAPI
from injector import Injector, Module, provider

from gateway.api import APIModule
from gateway.config import GatewayServiceConfigurations, provide_config
from gateway.core.services.registry import ServiceRegistry
from gateway.infrastructure import InfrastructureModule


class ProductionModule(Module):
    @provider
    def provide_service_registry(
        self, configurations: GatewayServiceConfigurations
    ) -> ServiceRegistry:
        return ServiceRegistry(
            services=configurations.services, public_keys=configurations.public_keys
        )


@lru_cache
def provide_injector() -> Injector:
    injector = Injector(
        modules=[
            provide_config,
            InfrastructureModule,
            APIModule,
            ProductionModule,
        ]
    )
    injector.get(FastAPI).state.injector = injector
    return injector
