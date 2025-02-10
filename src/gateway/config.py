import json
import os

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from injector import Binder
from pydantic_settings import BaseSettings

from gateway.core.services.service import Service

PUBLIC_KEY_EXT = ".pem"


class GatewayServiceConfigurations(BaseSettings):
    PUBLIC_KEY_BASE_FOLDER: str = "./keys"
    SERVICE_CONFIG_FILE: str = "./services.json"
    PORT: int = 8001
    CACHE_URL: str = "redis://127.0.0.1:63790/0"

    @property
    def public_keys(self) -> dict[str, RSAPublicKey]:
        public_keys = dict[str, RSAPublicKey]()
        for filename in os.listdir(self.PUBLIC_KEY_BASE_FOLDER):
            if filename.endswith(PUBLIC_KEY_EXT):
                with open(
                    os.path.join(self.PUBLIC_KEY_BASE_FOLDER, filename), mode="rb"
                ) as f:
                    public_key = serialization.load_pem_public_key(
                        f.read(), backend=default_backend()
                    )
                if not isinstance(public_key, RSAPublicKey):
                    raise TypeError(
                        f"Expected RSAPublicKey, but got {type(public_key).__name__}"
                    )
                public_keys[filename.rstrip(PUBLIC_KEY_EXT)] = public_key

        return public_keys

    @property
    def services(self) -> dict[str, dict[str, Service]]:
        with open(self.SERVICE_CONFIG_FILE, "r") as f:
            services_config = json.load(f)

        services = dict[str, dict[str, Service]]()
        for service_name, service_info in services_config.items():
            services[service_name] = {
                key: Service(
                    **value,
                    public_key=self.public_keys[service_name],
                    name=service_name,
                )
                for key, value in service_info.items()
            }

        return services


def provide_config(binder: Binder):
    binder.bind(GatewayServiceConfigurations)
