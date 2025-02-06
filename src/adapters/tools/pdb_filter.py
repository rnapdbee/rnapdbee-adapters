from collections import defaultdict
from typing import Callable, Dict, Iterable, Tuple

from rnapolis.transformer import replace_value

from adapters.tools import cif_filter, maxit


class DefaultMapping(defaultdict):
    def __missing__(self, key):
        return key


def apply(
    file_content: str, functions_args: Iterable[Tuple[Callable, Dict]]
) -> Tuple[str, Dict[str, str]]:
    # apply all filters on mmCIF representation
    cif_content = cif_filter.apply(file_content, functions_args)

    # rename chains to printable, single characters
    cif_content, mapping = replace_value(
        cif_content,
        "atom_site",
        "auth_asym_id",
        string.ascii_uppercase
        + string.digits
        + string.ascii_lowercase
        + string.punctuation,
    )
    mapping = {v: k for k, v in mapping.items()}

    # convert back to PDB
    pdb_content = maxit.ensure_pdb(cif_content)
    return pdb_content, mapping
