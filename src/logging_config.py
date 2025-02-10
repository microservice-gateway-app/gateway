import logging
from uvicorn.config import LOGGING_CONFIG


def config_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-5s %(message)s",
        handlers=[
            logging.StreamHandler(),
        ],
    )

    access_fmt = '%(asctime)s %(levelprefix)s %(client_addr)s - "%(request_line)s" %(status_code)s'
    default_fmt = "%(asctime)s %(levelprefix)s %(message)s"
    LOGGING_CONFIG["formatters"]["access"]["fmt"] = access_fmt
    LOGGING_CONFIG["formatters"]["default"]["fmt"] = default_fmt
