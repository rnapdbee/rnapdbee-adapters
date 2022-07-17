import orjson
from functools import wraps
from flask import Response, request
from http import HTTPStatus


def is_cif(file_content: str) -> bool:
    for line in file_content.splitlines():
        if line.startswith('_atom_site'):
            return True
    return False


def content_type(mimetype: str):

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

    def _plain_response(function):

        @wraps(function)
        def __plain_response(*args, **kwargs):
            result = function(*args, **kwargs)
            return Response(response=result, status=HTTPStatus.OK, mimetype='text/plain')

        return __plain_response

    return _plain_response
