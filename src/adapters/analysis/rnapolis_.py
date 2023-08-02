#! /usr/bin/env python
# IMPORTANT! this file cannot be named rnapolis.py, because it imports from "rnapolis", and Python complains about that

import logging
import sys
import tempfile
from typing import Any, Dict

import orjson
import rnapolis.annotator
import rnapolis.parser
from rnapolis.common import Structure2D

logger = logging.getLogger(__name__)


def analyze(file_content: str, **kwargs: Dict[str, Any]) -> Structure2D:
    model = int(kwargs.get('model'))
    with tempfile.NamedTemporaryFile('w+') as cif_file:
        cif_file.write(file_content)
        cif_file.seek(0)
        tertiary_structure = rnapolis.parser.read_3d_structure(cif_file, model)
    secondary_structure = rnapolis.annotator.extract_secondary_structure(tertiary_structure, model)
    logger.debug(secondary_structure)
    return secondary_structure


def main() -> None:
    structure = analyze(sys.stdin.read(), model=1)
    print(orjson.dumps(structure).decode('utf-8'))


if __name__ == '__main__':
    main()
