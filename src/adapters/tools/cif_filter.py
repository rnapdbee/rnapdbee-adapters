from tempfile import NamedTemporaryFile, _TemporaryFileWrapper
from typing import Any, Callable, Dict, Iterable, List, Tuple

import mmcif.io

from adapters.tools import maxit


def apply(file_content: str, functions_args: Iterable[Tuple[Callable, Dict]]) -> str:
    with NamedTemporaryFile("w+", suffix=".cif") as cif_file:
        data = begin(cif_file, file_content)

        for function, kwargs in functions_args:
            function(data, **kwargs)

        cif_content = end(cif_file, data)
    return cif_content


def begin(cif: _TemporaryFileWrapper, file_content: str) -> List[Any]:
    cif.write(maxit.ensure_mmcif(file_content))
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
                for _, row in enumerate(atom_site.getRowList()):  # type: ignore
                    try:
                        float(row[occupancy])
                    except (KeyError, ValueError):
                        row[occupancy] = "1.0"


# Remove all atoms which belong to proteins
def remove_proteins(data: List, *_):
    if len(data) > 0:
        entity_poly = data[0].getObj("entity_poly")
        atom_site = data[0].getObj("atom_site")

        if entity_poly and atom_site:
            entity_id = entity_poly.getAttributeIndex("entity_id")
            type_ = entity_poly.getAttributeIndex("type")

            if entity_id != -1 and type_ != -1:
                id_type_map = {
                    row[entity_id]: row[type_] for row in entity_poly.getRowList()
                }
            else:
                id_type_map = {}

            label_entity_id = atom_site.getAttributeIndex("label_entity_id")

            if label_entity_id != -1:
                toremove = []

                for i, row in enumerate(atom_site.getRowList()):
                    entity_type = id_type_map.get(row[label_entity_id], "other")

                    # see: https://mmcif.wwpdb.org/dictionaries/mmcif_pdbx_v50.dic/Items/_entity_poly.type.html
                    if entity_type in [
                        "cyclic-pseudo-peptide",
                        "polypeptide(D)",
                        "polypeptide(L)",
                    ]:
                        toremove.append(i)

                for i in reversed(toremove):
                    del atom_site.getRowList()[i]
