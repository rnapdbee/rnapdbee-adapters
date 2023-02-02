import subprocess
import os
import logging
import signal
from tempfile import TemporaryDirectory, NamedTemporaryFile
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from functools import wraps
from http import HTTPStatus
from os import devnull

import orjson
from flask import Response, request
from werkzeug.exceptions import UnsupportedMediaType

from adapters.config import config
from adapters.exceptions import InvalidSvgError

logger = logging.getLogger(__name__)


def is_cif(file_content: str) -> bool:
    for line in file_content.splitlines():
        if line.startswith('_atom_site'):
            return True
    return False


def clean_svg(svg_content: str, copy_on_error: bool = False) -> str:
    """Clean SVG using svgcleaner

    Args:
        svg_content (str): content of SVG file
        copy_on_error(bool): whether copy original file on error. Defaults to False

    Raises:
        FileNotFoundError: conversion failed
        InvalidSvgError: conversion failed

    Returns:
        str: content of clean SVG file
    """

    with TemporaryDirectory() as directory:
        with NamedTemporaryFile('w+', dir=directory, suffix='.svg') as input_svg:
            input_svg.write(svg_content)
            input_svg.seek(0)
            output_svg = os.path.join(directory, 'output.svg')
            cmd_args = ['svgcleaner', input_svg.name, output_svg]
            if copy_on_error:
                cmd_args.append('--copy-on-error')
            run_external_cmd(cmd_args, cwd=directory)
        if not os.path.isfile(output_svg):
            raise FileNotFoundError('svgcleaner failed: SVG was not generated!')
        with open(output_svg, 'r', encoding='utf-8') as output_svg_file:
            clean_svg_content = output_svg_file.read()
        if 'svg' not in clean_svg_content:
            raise InvalidSvgError('svgcleaner failed: generated file is not valid SVG!')
    return clean_svg_content


def pdf_to_svg(pdf_path: str) -> str:
    """Convert PDF to SVG using pdf2svg

    Args:
        pdf_path (str): path to existing PDF file

    Raises:
        FileNotFoundError: conversion failed
        InvalidSvgError: conversion failed

    Returns:
        str: content of SVG file
    """

    with TemporaryDirectory() as directory:
        output_svg = os.path.join(directory, 'out.svg')
        run_external_cmd(
            ['pdf2svg', pdf_path, output_svg],
            cwd=directory,
        )
        if not os.path.isfile(output_svg):
            raise FileNotFoundError('pdf2svg: Output SVG does not exist!')
        with open(output_svg, 'r', encoding='utf-8') as svg_file:
            svg_content = svg_file.read()
        if 'svg' not in svg_content:
            raise InvalidSvgError('pdf2svg: Generated file is not valid SVG!')
    return svg_content


def run_external_cmd(
    args,
    cwd,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.PIPE,
    check=False,
    timeout=config["SUBPROCESS_DEFAULT_TIMEOUT"],
    cmd_input=None,
):
    """Wrapper for subprocess.Popen()

    Args:
        args: command arguments
        cwd (_type_): current working directory
        stdout (_type_, optional): target of stdout. Defaults to subprocess.DEVNULL.
        stderr (_type_, optional): target of stderr. Defaults to subprocess.PIPE.
        check (bool, optional): check for exceptions. Defaults to False.
        timeout (int, optional): timeout for command. Defaults to 120.
        cmd_input (bytes, optional): input for command. Defaults to None.

    Raises:
        ValueError: cwd is not valid directory

    Returns:
        result of subprocess.Popen()
    """

    if cwd is None:
        return ValueError('cwd argument must be valid directory!')

    subprocess_result = wrapped_popen(
        args,
        cwd=cwd,
        stdout=stdout,
        stderr=stderr,
        check=check,
        timeout=timeout,
        input=cmd_input,
    )

    error_output = subprocess_result.stderr.decode('utf-8')
    if error_output:
        logger.debug(f'Subprocess {args} stderr: {error_output}')

    return subprocess_result


def wrapped_popen(
    *popenargs,
    input=None,
    capture_output=False,
    timeout=None,
    check=False,
    **kwargs,
) -> subprocess.CompletedProcess:
    """Wrapper for subprocess.popen() (POSIX only)"""
    if input is not None:
        if kwargs.get('stdin') is not None:
            raise ValueError('stdin and input arguments may not both be used.')
        kwargs['stdin'] = subprocess.PIPE

    if capture_output:
        if kwargs.get('stdout') is not None or kwargs.get('stderr') is not None:
            raise ValueError('stdout and stderr arguments may not be used '
                             'with capture_output.')
        kwargs['stdout'] = subprocess.PIPE
        kwargs['stderr'] = subprocess.PIPE

    with subprocess.Popen(*popenargs, **kwargs, start_new_session=True) as process:
        try:
            stdout, stderr = process.communicate(input, timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            process.wait()
            raise
        except:  # noqa (Including KeyboardInterrupt, communicate handled that.)
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            # We don't call process.wait() as .__exit__ does that for us.
            raise
        retcode = process.poll()
        if check and retcode:
            raise subprocess.CalledProcessError(retcode, process.args, output=stdout, stderr=stderr)

    return subprocess.CompletedProcess(process.args, retcode, stdout, stderr)


def convert_to_svg_using_inkscape(file_content: str, file_type: str) -> str:
    """Convert file_type -> SVG using Inkscape

    Args:
        file_content (str): content of file as string
        file_type (str): e.g. .eps, .ps, .png, .jpg

    Raises:
        FileNotFoundError: Subprocess of Inkscape failed
        InvalidSvgError: Subprocess of Inkscape failed

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
                raise FileNotFoundError("Inkscape conversion failed: file does not exist!")
            with open(output_file, encoding='utf-8') as svg_file:
                svg_content = svg_file.read()
    if 'svg' not in svg_content:
        raise InvalidSvgError("Inkscape conversion failed: SVG not valid!")
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
                raise UnsupportedMediaType()
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
            logger.info(f'Response application/json sent (path: {request.path})')
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
            logger.info(f'Response text/plain sent (path: {request.path})')
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
            try:
                clean_svg_content = clean_svg(svg_content, copy_on_error=True)
            except (FileNotFoundError, InvalidSvgError, subprocess.SubprocessError):
                logger.warning('svgcleaner failed, returning non-optimized svg')
                logger.debug(f'invalid svg for svgcleaner: {svg_content}')
                clean_svg_content = svg_content
            logger.info(f'Response image/svg+xml sent (path: {request.path})')
            return Response(response=clean_svg_content, status=HTTPStatus.OK, mimetype='image/svg+xml')

        return __svg_response

    return _svg_response


@contextmanager
def suppress_stdout_stderr():
    """A context manager that redirects stdout and stderr to devnull"""
    with open(devnull, 'w', encoding='utf-8') as fnull:
        with redirect_stderr(fnull) as err, redirect_stdout(fnull) as out:
            yield (err, out)
