import string
import tempfile
from collections import defaultdict
from typing import Callable, Dict, Iterable, Optional, Tuple

from mmcif.io.IoAdapterPy import IoAdapterPy
from rnapolis.transformer import replace_value

from adapters.tools import cif_filter, maxit


class DefaultMapping(defaultdict):
    def __missing__(self, key):
        return key


def apply(
    file_content: str, functions_args: Iterable[Tuple[Callable, Dict]]
) -> Optional[Tuple[str, Dict[str, str]]]:
    # apply all filters on mmCIF representation
    cif_content = cif_filter.apply(file_content, functions_args)

    # check if the filtered data is PDB-compatible
    adapter = IoAdapterPy()

    with tempfile.NamedTemporaryFile(mode="wt") as f:
        f.write(file_content)
        f.seek(0)
        data = adapter.readFile(f.name)

    # no "atom_site" category -> not a PDB file
    if len(data) == 0 or "atom_site" not in data[0].getObjNameList():
        return None

    category_obj = data[0].getObj("atom_site")
    attributes = category_obj.getAttributeList()

    # no "auth_asym_id" column -> not a PDB file
    if "auth_asym_id" not in attributes:
        return None

    used = set()

    for row in category_obj.getRowList():
        i = attributes.index("auth_asym_id")
        used.add(row[i])

    available_chain_names = (
        string.ascii_uppercase
        + string.digits
        + string.ascii_lowercase
        + string.punctuation
    )

    # not enough unique chain names -> not possible to represent as a PDB file
    if len(used) > len(available_chain_names):
        return None

    # rename chains to printable, single characters
    cif_content, mapping = replace_value(
        cif_content,
        "atom_site",
        "auth_asym_id",
        available_chain_names,
    )
    mapping = {v: k for k, v in mapping.items()}

    # convert back to PDB
    pdb_content = maxit.ensure_pdb(cif_content)
    return pdb_content, mapping
