import logging

config = {
    "CACHE_TYPE": "FileSystemCache",
    "CACHE_DIR": "/var/tmp/adapters_cache/",
    "CACHE_THRESHOLD": 50,
    "CACHE_DEFAULT_TIMEOUT": 3600,
    "SUBPROCESS_DEFAULT_TIMEOUT": 120,
}

logging.basicConfig(
    format='[%(asctime)s] [%(levelname)s] [%(filename)s] %(message)s',
    level='WARNING',
)
