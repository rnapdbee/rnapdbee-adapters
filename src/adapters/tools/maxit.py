#! /usr/bin/env python
import logging
import os
import sys
from tempfile import NamedTemporaryFile

import mmcif.io
from rnapolis.quick_filter import filter_content

from adapters.cli2rest_client import cli2rest_run_single
from adapters.tools.utils import is_cif

logger = logging.getLogger(__name__)
base_url = os.getenv("CLI2REST_MAXIT_URL", "http://localhost:8000")

UNKNOWN_VALUES = {".", "?", ""}


def normalize_label_chains(cif_content: str) -> str:
    """Restore polymer label chains to the corresponding author chains.

    Some upstream tools (notably Bio.PDB's MMCIFIO) split a polymer into
    several ``label_asym_id`` values at modified residues while keeping one
    ``auth_asym_id``. MAXIT then interprets the leading fragments as ligands
    and renumbers them (e.g. residues 5, 6, 7 become 105, 106, 107). Restoring
    label chains for polymeric rows prevents that.
    """
    with NamedTemporaryFile("w+", suffix=".cif") as input_file:
        input_file.write(cif_content)
        input_file.flush()
        data = mmcif.io.IoAdapter().readFile(input_file.name)

    changed = False
    for block in data:
        atom_site = block.getObj("atom_site")
        if atom_site is None:
            continue

        label_chain = atom_site.getAttributeIndex("label_asym_id")
        auth_chain = atom_site.getAttributeIndex("auth_asym_id")
        label_seq = atom_site.getAttributeIndex("label_seq_id")
        if label_chain == -1 or auth_chain == -1:
            continue

        rows = atom_site.getRowList()
        labels_per_auth_chain: dict[str, set[str]] = {}
        for row in rows:
            if label_seq != -1 and str(row[label_seq]).strip() in UNKNOWN_VALUES:
                continue
            labels_per_auth_chain.setdefault(row[auth_chain], set()).add(
                row[label_chain]
            )

        ambiguous = {
            chain for chain, labels in labels_per_auth_chain.items() if len(labels) > 1
        }
        if not ambiguous:
            continue

        logger.info(
            "Normalizing label chains for ambiguous auth chains: %s",
            sorted(ambiguous),
        )
        for row in rows:
            if label_seq != -1 and str(row[label_seq]).strip() in UNKNOWN_VALUES:
                continue
            if row[auth_chain] in ambiguous:
                row[label_chain] = row[auth_chain]
                changed = True

    if not changed:
        return cif_content

    with NamedTemporaryFile("w+", suffix=".cif") as output_file:
        output_path = output_file.name
        mmcif.io.IoAdapter().writeFile(output_path, data)
        with open(output_path) as reader:
            return reader.read()


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
        return normalize_label_chains(file_content)
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
    cif_content = normalize_label_chains(cif_content)
    return cli2rest_run_single(
        base_url=base_url,
        input_file_content=cif_content,
        input_file_extension=".cif",
        output_file="output.pdb",
        config_name="maxit/config-cif2pdb.yaml",
    )


def cif2mmcif(cif_content: str) -> str:
    cif_content = normalize_label_chains(cif_content)
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
