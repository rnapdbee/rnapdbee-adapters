from contextlib import contextmanager, redirect_stderr, redirect_stdout
from functools import wraps
from http import HTTPStatus
from os import devnull

import orjson
from flask import Response, request


def is_cif(file_content: str) -> bool:
    for line in file_content.splitlines():
        if line.startswith('_atom_site'):
            return True
    return False


def content_type(mimetype: str):
    """Decorate a flask route to check `Content-Type` in request header.
    If `Content-Type` is not equal `mimetype` returns `415 Unsupported Media Type`.

    Args:
        mimetype (str): required value of `Content-Type` header
    """

    def _content_type(function):

        @wraps(function)
        def __content_type(*args, **kwargs):
            if request.headers['Content-Type'] != mimetype:
                return Response(status=HTTPStatus.UNSUPPORTED_MEDIA_TYPE)
            result = function(*args, **kwargs)
            return result

        return __content_type

    return _content_type


def json_response():
    """Decorate a flask route to return `Response` with status `200`and
    `Content-Type: application/json`. Additionally, `orjson` is used to dump object.
    """

    def _json_response(function):

        @wraps(function)
        def __json_response(*args, **kwargs):
            result = function(*args, **kwargs)
            return Response(response=orjson.dumps(result).decode('utf-8'),
                            status=HTTPStatus.OK,
                            mimetype='application/json')

        return __json_response

    return _json_response


def plain_response():
    """Decorate a flask route to return `Response` with status `200` and
    `Content-Type: text/plain`.
    """

    def _plain_response(function):

        @wraps(function)
        def __plain_response(*args, **kwargs):
            result = function(*args, **kwargs)
            return Response(response=result, status=HTTPStatus.OK, mimetype='text/plain')

        return __plain_response

    return _plain_response


@contextmanager
def suppress_stdout_stderr():
    """A context manager that redirects stdout and stderr to devnull"""
    with open(devnull, 'w', encoding='utf-8') as fnull:
        with redirect_stderr(fnull) as err, redirect_stdout(fnull) as out:
            yield (err, out)
