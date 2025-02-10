from __future__ import annotations

import logging

import uvicorn

from gateway.api import GatewayApp
from gateway.module import provide_injector

logging.basicConfig(
    format="%(levelname)s [%(asctime)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.DEBUG,
)
injector = provide_injector()
gateway = injector.get(GatewayApp)
app = gateway.app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
