#! /usr/bin/env python
# IMPORTANT! this file cannot be named rnapolis.py, because it imports from "rnapolis", and Python complains about that

import tempfile
import sys

import orjson
import rnapolis.annotator
import rnapolis.parser
from rnapolis.common import Structure2D


def analyze(file_content: str, model: int) -> Structure2D:
    with tempfile.NamedTemporaryFile('w+') as cif_file:
        cif_file.write(file_content)
        cif_file.seek(0)
        tertiary_structure = rnapolis.parser.read_3d_structure(cif_file, model)

    return rnapolis.annotator.extract_secondary_structure(tertiary_structure, model)


def main() -> None:
    structure = analyze(sys.stdin.read(), 1)
    print(orjson.dumps(structure).decode('utf-8'))


if __name__ == '__main__':
    main()
