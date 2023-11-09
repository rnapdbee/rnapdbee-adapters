#! /usr/bin/env python

import datetime
import logging
import subprocess

import orjson
from flask import Flask, Response, request
from werkzeug.exceptions import HTTPException

from adapters.cache import cache
from adapters.config import config
from adapters.routes.analysis import server as analysis
from adapters.routes.conversion import server as conversion
from adapters.routes.filtering import server as filtering
from adapters.routes.visualization import server as visualization

app = Flask(__name__)
app.config.from_mapping(config)

logger = logging.getLogger(__name__)


@analysis.before_request
@conversion.before_request
@filtering.before_request
def log_plain_request():
    logger.info(f"Request (text/plain) received, path: {request.path}")
    logger.debug(request.data.decode("utf-8"))


@visualization.before_request
def log_json_request():
    logger.info(f"Request (application/json) received, path: {request.path}")
    logger.debug(orjson.loads(request.data))


@app.errorhandler(Exception)
def handle_exception(exception: Exception):
    if isinstance(exception, HTTPException):
        name = exception.name
        code = exception.code
        description = exception.description
    elif isinstance(exception, subprocess.TimeoutExpired):
        name = "Bad Request"
        code = 400
        description = "Timeout (request too big)"
        logger.warning(
            f"Subprocess timeout for {exception.cmd} after {exception.timeout}s"
        )
    else:
        code = 500
        name = "Internal Server Error"
        description = "Unknown Error"
        logger.error(f"{type(exception).__name__}: {exception}", exc_info=1)

    result = {
        "error": {
            "code": code,
            "name": name,
            "description": description,
            "timestamp": datetime.datetime.now(),
            "path": request.path,
        },
    }

    return Response(
        response=orjson.dumps(result).decode("utf-8"),
        status=code,
        mimetype="application/json",
    )


cache.init_app(app)
app.register_blueprint(analysis, url_prefix="/analysis-api/v1")
app.register_blueprint(conversion, url_prefix="/conversion-api/v1")
app.register_blueprint(filtering, url_prefix="/filtering-api/v1")
app.register_blueprint(visualization, url_prefix="/visualization-api/v1")

if __name__ == "__main__":
    app.run()
