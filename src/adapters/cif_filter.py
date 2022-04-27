import tempfile

import mmcif.io

from adapters import maxit


def filter_by_model(file_content: str, model: int = 1) -> str:
    '''
    Leave only one specified model in the file and sets its number to 1. Some tools like BPNET work only with model number 1.
    :param file_content: A PDB or PDBx/mmCIF file contents.
    :param model: The desired model to keep (all other will be discarded)
    :return: A PDBx/mmCIF file contents modified by discarding not needed models
    '''
    cif = tempfile.NamedTemporaryFile('w+', suffix='.cif')
    cif.write(maxit.ensure_cif(file_content))
    cif.seek(0)

    adapter = mmcif.io.IoAdapter()
    data = adapter.readFile(cif.name)

    container = data[0]
    atom_site = container.getObj('atom_site')
    pdbx_PDB_model_num = atom_site.getAttributeIndex('pdbx_PDB_model_num')

    if pdbx_PDB_model_num != -1:
        toremove = []
        for i, row in enumerate(atom_site.getRowList()):
            if int(row[pdbx_PDB_model_num]) != model:
                toremove.append(i)
            else:
                row[pdbx_PDB_model_num] = '1'
        for i in reversed(toremove):
            del atom_site.getRowList()[i]

    cif.seek(0)
    cif.truncate(0)

    adapter.writeFile(cif.name, data)

    cif.seek(0)
    return cif.read()


def fix_occupancy(file_content: str) -> str:
    cif = tempfile.NamedTemporaryFile('w+', suffix='.cif')
    cif.write(maxit.ensure_cif(file_content))
    cif.seek(0)

    adapter = mmcif.io.IoAdapter()
    data = adapter.readFile(cif.name)

    container = data[0]
    atom_site = container.getObj('atom_site')
    occupancy = atom_site.getAttributeIndex('occupancy')

    if occupancy != -1:
        for i, row in enumerate(atom_site.getRowList()):
            try:
                _ = float(row[occupancy])
            except:
                row[occupancy] = '1.0'

    cif.seek(0)
    cif.truncate(0)

    adapter.writeFile(cif.name, data)

    cif.seek(0)
    return cif.read()
