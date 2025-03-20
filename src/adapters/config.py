import logging
from os import environ

config = {
    "CACHE_TYPE": "FileSystemCache",
    "CACHE_DIR": environ.get("ADAPTERS_CACHE_DIR", "/var/tmp/adapters_cache/"),
    "CACHE_THRESHOLD": int(environ.get("ADAPTERS_CACHE_THRESHOLD", "50")),
    "CACHE_DEFAULT_TIMEOUT": int(environ.get("ADAPTERS_CACHE_TIMEOUT", "3600")),
    "SUBPROCESS_DEFAULT_TIMEOUT": int(
        environ.get("ADAPTERS_SUBPROCESS_TIMEOUT", "600")
    ),
    "FR3D_SERVICE_URL": environ.get("FR3D_SERVICE_URL", "http://localhost:8080"),
}

logging.basicConfig(format="[%(asctime)s] [%(levelname)s] [%(filename)s] %(message)s")
logging.getLogger(__name__.split(".", maxsplit=1)[0]).setLevel(
    environ.get("ADAPTERS_FLASK_LOG_LEVEL", "INFO")
)
