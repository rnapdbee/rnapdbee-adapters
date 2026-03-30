#! /usr/bin/env python
import logging
import os
import sys

from rnapolis.quick_filter import filter_content

from adapters.cli2rest_client import cli2rest_run_single
from adapters.tools.utils import is_cif

logger = logging.getLogger(__name__)
base_url = os.getenv("CLI2REST_MAXIT_URL", "http://localhost:8000")


def ensure_cif(file_content: str) -> str:
    file_content = filter_content(
        content=file_content,
        mode="nucleic-acid",
        keep_ligands=True,
        keep_waters=False,
        keep_ions=True,
        chains=None,  # leave all chains
        model=None,  # leave all models
    )

    if is_cif(file_content):
        return file_content
    return pdb2cif(file_content)


def ensure_pdb(file_content: str) -> str:
    file_content = filter_content(
        content=file_content,
        mode="nucleic-acid",
        keep_ligands=True,
        keep_waters=False,
        keep_ions=True,
        chains=None,  # leave all chains
        model=None,  # leave all models
    )

    if is_cif(file_content):
        return cif2pdb(file_content)
    return file_content


def ensure_mmcif(file_content: str) -> str:
    return cif2mmcif(ensure_cif(file_content))


def pdb2cif(pdb_content: str) -> str:
    return cli2rest_run_single(
        base_url=base_url,
        input_file_content=pdb_content,
        input_file_extension=".pdb",
        output_file="output.cif",
        config_name="maxit/config-pdb2cif.yaml",
    )


def cif2pdb(cif_content: str) -> str:
    return cli2rest_run_single(
        base_url=base_url,
        input_file_content=cif_content,
        input_file_extension=".cif",
        output_file="output.pdb",
        config_name="maxit/config-cif2pdb.yaml",
    )


def cif2mmcif(cif_content: str) -> str:
    return cli2rest_run_single(
        base_url=base_url,
        input_file_content=cif_content,
        input_file_extension=".cif",
        output_file="output.cif",
        config_name="maxit/config-cif2mmcif.yaml",
    )


def main():
    with open(sys.argv[1]) as f:
        print(ensure_mmcif(f.read()))


if __name__ == "__main__":
    main()
