import re
from collections import defaultdict
from typing import Callable, Dict, Iterable, Tuple

from rnapolis.transformer import replace_value

from adapters.exceptions import PdbParsingError
from adapters.tools import maxit


class DefaultMapping(defaultdict):
    def __missing__(self, key):
        return key


def apply(
    file_content: str, functions_args: Iterable[Tuple[Callable, Dict]]
) -> Tuple[str, Dict[str, str]]:
    # replace chains with one letter names if the input is an mmCIF file
    if re.search(r"^_atom_site", file_content, re.MULTILINE):
        pdb_content, mapping = replace_value(file_content, "atom_site", "auth_asym_id")
        mapping = {v: k for k, v in mapping.items()}
    else:
        pdb_content, mapping = file_content, DefaultMapping()

    pdb_content = maxit.ensure_pdb(pdb_content)

    for function, kwargs in functions_args:
        pdb_content = function(pdb_content, **kwargs)

    return pdb_content, mapping


def leave_single_model(file_content: str, **kwargs) -> str:
    model = int(kwargs.get("model", 1))

    append_mode = True
    new_content_arr = []
    models_count = 0

    for line in file_content.splitlines(True):
        if line.startswith("MODEL"):
            current_model = int(line[10:14].strip())
            models_count += 1
            append_mode = current_model == model
        elif line.startswith("ENDMDL"):
            append_mode = True
        elif append_mode:
            new_content_arr.append(line)

    # Only one model in original file
    if models_count == 0:
        models_count = 1

    if model > models_count or model < 1:
        raise PdbParsingError(
            f"File has {models_count} model(s), number {model} passed."
        )

    new_content = "".join(new_content_arr)
    return new_content
