#!/bin/bash
set -e

exec gunicorn \
    --worker-tmp-dir /dev/shm \
    --workers ${ADAPTERS_WORKERS} \
    --threads ${ADAPTERS_THREADS} \
    --timeout ${ADAPTERS_WORKER_TIMEOUT} \
    --log-level ${ADAPTERS_GUNICORN_LOG_LEVEL} \
    --max-requests ${ADAPTERS_MAX_REQUESTS} \
    --bind 0.0.0.0:80 \
    adapters.server:app
