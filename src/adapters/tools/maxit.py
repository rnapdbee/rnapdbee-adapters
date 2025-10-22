#! /usr/bin/env python
import logging
import os
import sys

from tempfile import TemporaryDirectory

from adapters.cli2rest_client import cli2rest_process
from adapters.tools.utils import is_cif

logger = logging.getLogger(__name__)
base_url = os.getenv("CLI2REST_MAXIT_URL", "http://localhost:8000")


def ensure_cif(file_content: str) -> str:
    if is_cif(file_content):
        return file_content
    return pdb2cif(file_content)


def ensure_pdb(file_content: str) -> str:
    if is_cif(file_content):
        return cif2pdb(file_content)
    return file_content


def ensure_mmcif(file_content: str) -> str:
    return cif2mmcif(ensure_cif(file_content))


def cli2rest_convert(
    file_content: str, extension: str, config_name: str, output_file: str
) -> str:
    with TemporaryDirectory() as directory:
        input_file = os.path.join(directory, f"input{extension}")

        with open(input_file, "w") as f:
            f.write(file_content)

        cli2rest_process(base_url, input_file, config_name, directory)

        with open(os.path.join(directory, output_file)) as f:
            return f.read()


def pdb2cif(pdb_content) -> str:
    return cli2rest_convert(
        file_content=pdb_content,
        extension=".pdb",
        config_name="maxit/config-pdb2cif.yaml",
        output_file="output.cif",
    )


def cif2pdb(cif_content) -> str:
    return cli2rest_convert(
        file_content=cif_content,
        extension=".cif",
        config_name="maxit/config-cif2pdb.yaml",
        output_file="output.pdb",
    )


def cif2mmcif(cif_content: str) -> str:
    return cli2rest_convert(
        file_content=cif_content,
        extension=".cif",
        config_name="maxit/config-cif2mmcif.yaml",
        output_file="output.cif",
    )


def main():
    with open(sys.argv[1]) as f:
        print(ensure_mmcif(f.read()))


if __name__ == "__main__":
    main()
