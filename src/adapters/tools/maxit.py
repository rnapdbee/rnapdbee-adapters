#! /usr/bin/env python
import sys
from tempfile import NamedTemporaryFile, TemporaryDirectory

from adapters.tools.utils import is_cif, run_external_cmd
from adapters.cache import cache

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


@cache.memoize()
def pdb2cif(pdb_content):
    with TemporaryDirectory() as directory:
        pdb = NamedTemporaryFile('w+', suffix='.pdb', dir=directory)
        pdb.write(pdb_content)
        pdb.seek(0)
        cif = NamedTemporaryFile('w+', suffix='.cif', dir=directory)
        run_external_cmd(
            ['maxit', '-input', pdb.name, '-output', cif.name, '-o', MODE_PDB2CIF],
            cwd=directory,
        )
        cif.seek(0)
        cif_content = cif.read()

    return cif_content


@cache.memoize()
def cif2pdb(cif_content):
    with TemporaryDirectory() as directory:
        cif = NamedTemporaryFile('w+', suffix='.cif', dir=directory)
        cif.write(cif_content)
        cif.seek(0)
        pdb = NamedTemporaryFile('w+', suffix='.pdb', dir=directory)
        run_external_cmd(
            ['maxit', '-input', cif.name, '-output', pdb.name, '-o', MODE_CIF2PDB],
            cwd=directory,
        )
        pdb.seek(0)
        pdb_content = pdb.read()

    return pdb_content


def main():
    print(ensure_cif(sys.stdin.read()))


if __name__ == '__main__':
    main()
