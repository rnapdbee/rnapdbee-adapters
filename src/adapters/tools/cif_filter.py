import itertools
import string
from tempfile import NamedTemporaryFile, _TemporaryFileWrapper
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

import mmcif.io

from adapters.tools import maxit


def apply(
    file_content: str,
    functions_args: Iterable[Tuple[Callable, Dict]],
    mmcif_ensured: bool = False,
) -> str:
    if mmcif_ensured:
        cif_content = file_content
    else:
        cif_content = maxit.ensure_mmcif(file_content)

    # apply all filtering functions
    with NamedTemporaryFile("w+", suffix=".cif") as cif_file:
        data = begin(cif_file, cif_content)

        for function, kwargs in functions_args:
            function(data, **kwargs)

        cif_content = end(cif_file, data)

    return cif_content


def begin(cif: _TemporaryFileWrapper, file_content: str) -> List[Any]:
    cif.write(file_content)
    cif.flush()
    cif.seek(0)
    return mmcif.io.IoAdapter().readFile(cif.name)


def end(cif: _TemporaryFileWrapper, data: List[Any]) -> str:
    cif.seek(0)
    cif.truncate(0)
    mmcif.io.IoAdapter().writeFile(cif.name, data)
    cif.flush()
    cif.seek(0)
    return cif.read()


# Leave only one specified model in the file and sets its number to 1.
# Some tools like BPNET work only with model number 1.
def leave_single_model(data: List, **kwargs):
    model = kwargs.get("model", 1)

    if len(data) > 0:
        atom_site = data[0].getObj("atom_site")

        if atom_site:
            pdbx_PDB_model_num = atom_site.getAttributeIndex("pdbx_PDB_model_num")

            if pdbx_PDB_model_num != -1:
                toremove = []

                for i, row in enumerate(atom_site.getRowList()):
                    if int(row[pdbx_PDB_model_num]) != model:
                        toremove.append(i)
                    else:
                        row[pdbx_PDB_model_num] = "1"
                for i in reversed(toremove):
                    del atom_site.getRowList()[i]


# Modify occupancy column so that it always parses to a float
def fix_occupancy(data: List, *_):
    if len(data) > 0:
        atom_site = data[0].getObj("atom_site")

        if atom_site:
            occupancy = atom_site.getAttributeIndex("occupancy")

            if occupancy != -1:
                for row in atom_site.getRowList():
                    try:
                        float(row[occupancy])
                    except (KeyError, ValueError):
                        row[occupancy] = "1.0"


def _generate_chain_names():
    """Generate unlimited safe chain names: A-Z, a-z, 0-9, AA, AB, ..."""
    chars = string.ascii_uppercase + string.ascii_lowercase + string.digits
    length = 1
    while True:
        for combo in itertools.product(chars, repeat=length):
            yield "".join(combo)
        length += 1


def sanitize_chains(cif_content: str) -> Tuple[str, Dict[str, Optional[str]]]:
    """Replace auth_asym_id values with safe alphanumeric chain names.

    Some tools (e.g., FR3D) cannot process mmCIF files where auth_asym_id
    is "?" or "." (the mmCIF convention for unknown/missing values, typically
    produced by MAXIT when converting PDB files with blank chain identifiers).

    This function renames all auth_asym_id values to safe alphanumeric names
    and returns an inverted mapping for later restoration via restore_chains.
    Values "?" and "." are normalized to None in the mapping.

    Returns:
        A tuple of (new_cif_content, mapped_chains) where mapped_chains is
        {new_chain_name: original_value_or_None}.
    """
    with NamedTemporaryFile("w+", suffix=".cif") as cif_file:
        data = begin(cif_file, cif_content)

        if len(data) == 0:
            return cif_content, {}

        atom_site = data[0].getObj("atom_site")
        if atom_site is None:
            return cif_content, {}

        auth_asym_id = atom_site.getAttributeIndex("auth_asym_id")
        if auth_asym_id == -1:
            return cif_content, {}

        # Build mapping from original chain names to new safe names
        mapping = {}
        name_gen = _generate_chain_names()
        for row in atom_site.getRowList():
            if row[auth_asym_id] not in mapping:
                mapping[row[auth_asym_id]] = next(name_gen)
            row[auth_asym_id] = mapping[row[auth_asym_id]]

        cif_content = end(cif_file, data)

    # Invert mapping: new_name -> original_value, normalizing "?" and "." to None
    mapped_chains = {
        new: (None if old in ("?", ".") else old) for old, new in mapping.items()
    }
    return cif_content, mapped_chains
