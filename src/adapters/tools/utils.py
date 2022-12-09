import subprocess
import os
from tempfile import TemporaryDirectory, NamedTemporaryFile
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from functools import wraps
from http import HTTPStatus
from os import devnull

import orjson
from flask import Response, request

from adapters.config import config


def is_cif(file_content: str) -> bool:
    for line in file_content.splitlines():
        if line.startswith('_atom_site'):
            return True
    return False


def run_external_cmd(
    args,
    cwd,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    check=False,
    timeout=config["SUBPROCESS_DEFAULT_TIMEOUT"],
    cmd_input=None,
):
    """Wrapper for subprocess.run()

    Args:
        args: command arguments
        cwd (_type_): current working directory
        stdout (_type_, optional): target of stdout. Defaults to subprocess.DEVNULL.
        stderr (_type_, optional): target of stderr. Defaults to subprocess.DEVNULL.
        check (bool, optional): check for exceptions. Defaults to False.
        timeout (int, optional): timeout for command. Defaults to 120.
        cmd_input (bytes, optional): input for command. Defaults to None.

    Returns:
        result of subprocess.run()
    """

    if cwd is None:
        return ValueError('cwd argument must be valid directory!')

    # TODO: change stderr=subprocess.PIPE and log it?
    return subprocess.run(
        args,
        cwd=cwd,
        stdout=stdout,
        stderr=stderr,
        check=check,
        timeout=timeout,
        input=cmd_input,
    )


def fix_using_rsvg_convert(svg_content: str) -> str:
    """Convert svg -> svg using rsvg-convert.
    Especially add viewBox attribute to SVG.
    Use this carefully since rsvg-convert make SVG bigger.

    Args:
        svg_content (str): SVG as string

    Raises:
        RuntimeError: Subprocess of rsvg-convert failed

    Returns:
        str: fixed SVG as string
    """

    with TemporaryDirectory() as directory:
        with NamedTemporaryFile('w+', dir=directory, suffix='.svg') as svg_file:
            svg_file.write(svg_content)
            svg_file.seek(0)
            fixed_svg_content = run_external_cmd(
                ['rsvg-convert', '-f', 'svg', svg_file.name],
                cwd=directory,
                stdout=subprocess.PIPE,
            ).stdout.decode('utf-8')
    if 'svg' not in fixed_svg_content:
        raise RuntimeError("rsvg-convert conversion failed!")
    return fixed_svg_content


def convert_to_svg_using_inkscape(file_content: str, file_type: str) -> str:
    """Convert file_type -> SVG using Inkscape

    Args:
        file_content (str): content of file as string
        file_type (str): e.g. .eps, .ps, .png, .jpg

    Raises:
        RuntimeError: Subprocess of Inkscape failed

    Returns:
        str: SVG content as string
    """

    with TemporaryDirectory() as directory:
        with NamedTemporaryFile('w+', dir=directory, suffix=file_type) as file:
            file.write(file_content)
            file.seek(0)
            output_file = os.path.join(directory, 'output.svg')
            run_external_cmd(
                [
                    'inkscape',
                    '--export-plain-svg',
                    '--export-area-drawing',
                    '--export-filename',
                    output_file,
                    file.name,
                ],
                cwd=directory,
            )
            if not os.path.isfile(output_file):
                raise RuntimeError("Inkscape conversion failed: file does not exist!")
            with open(output_file, encoding='utf-8') as svg_file:
                svg_content = svg_file.read()
    if 'svg' not in svg_content:
        raise RuntimeError("Inkscape conversion failed: SVG not valid!")
    return svg_content


def content_type(mimetype: str):
    """Decorate a flask route to check `Content-Type` in request header.
    If `Content-Type` is not equal `mimetype` returns `415 Unsupported Media Type`.

    Args:
        mimetype (str): required value of `Content-Type` header
    """

    def _content_type(function):

        @wraps(function)
        def __content_type(*args, **kwargs):
            if 'Content-Type' not in request.headers or request.headers['Content-Type'] != mimetype:
                return Response(status=HTTPStatus.UNSUPPORTED_MEDIA_TYPE)
            result = function(*args, **kwargs)
            return result

        return __content_type

    return _content_type


def json_response():
    """Decorate a flask route to return `Response` with status `200`and
    `Content-Type: application/json`. Additionally, `orjson` is used to dump object."""

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
    `Content-Type: text/plain`."""

    def _plain_response(function):

        @wraps(function)
        def __plain_response(*args, **kwargs):
            result = function(*args, **kwargs)
            return Response(response=result, status=HTTPStatus.OK, mimetype='text/plain')

        return __plain_response

    return _plain_response


def svg_response():
    """Decorate a flask route to return `Response` with status `200` and
    `Content-Type: image/svg+xml`."""

    def _svg_response(function):

        @wraps(function)
        def __svg_response(*args, **kwargs):
            svg_content = function(*args, **kwargs)
            return Response(response=svg_content, status=HTTPStatus.OK, mimetype='image/svg+xml')

        return __svg_response

    return _svg_response


@contextmanager
def suppress_stdout_stderr():
    """A context manager that redirects stdout and stderr to devnull"""
    with open(devnull, 'w', encoding='utf-8') as fnull:
        with redirect_stderr(fnull) as err, redirect_stdout(fnull) as out:
            yield (err, out)
