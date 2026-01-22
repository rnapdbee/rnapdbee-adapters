from tempfile import NamedTemporaryFile, _TemporaryFileWrapper
from typing import Any, Callable, Dict, Iterable, List, Tuple

import mmcif.io
from rnapolis.quick_filter import filter_content

from adapters.tools import maxit


def apply(
    file_content: str, model: int, functions_args: Iterable[Tuple[Callable, Dict]]
) -> str:
    # quick filter to remove non-nucleic acid content
    filtered_content = filter_content(
        content=file_content,
        mode="nucleic-acid",
        keep_ligands=True,
        keep_waters=False,
        keep_ions=True,
        keep_altlocs=False,
        chains=None,  # leave all chains among those filtered
        model=model,
    )

    # ensure the format is mmCIF
    cif_content = maxit.ensure_mmcif(filtered_content)

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
