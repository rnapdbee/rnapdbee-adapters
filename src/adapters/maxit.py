#! /usr/bin/env python
import subprocess
import sys
import tempfile

from adapters.utils import is_cif

# constants defined by MAXIT
MODE_PDB2CIF = '1'
MODE_CIF2PDB = '2'


def ensure_cif(file_content: str) -> str:
    if is_cif(file_content):
        return file_content
    return pdb2cif(file_content)


def ensure_pdb(file_content: str) -> str:
    if is_cif(file_content):
        return cif2pdb(file_content)
    return file_content


def pdb2cif(pdb_content):
    pdb = tempfile.NamedTemporaryFile('w+', suffix='.pdb')
    pdb.write(pdb_content)
    pdb.seek(0)
    cif = tempfile.NamedTemporaryFile('w+', suffix='.cif')
    subprocess.run(['maxit', '-input', pdb.name, '-output', cif.name, '-o', MODE_PDB2CIF])
    cif.seek(0)
    return cif.read()


def cif2pdb(cif_content):
    cif = tempfile.NamedTemporaryFile('w+', suffix='.cif')
    cif.write(cif_content)
    cif.seek(0)
    pdb = tempfile.NamedTemporaryFile('w+', suffix='.pdb')
    subprocess.run(['maxit', '-input', cif.name, '-output', pdb.name, '-o', MODE_CIF2PDB])
    pdb.seek(0)
    return pdb.read()


def main():
    print(ensure_cif(sys.stdin.read()))


if __name__ == '__main__':
    main()
