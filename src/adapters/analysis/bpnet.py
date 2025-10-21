#! /usr/bin/env python
import logging
import os
import sys
from tempfile import TemporaryDirectory
from typing import Any, Dict

import orjson
from rnapolis.adapter import parse_external_output, ExternalTool
from rnapolis.common import BaseInteractions
from rnapolis.parser import read_3d_structure

from adapters.cli2rest_client import cli2rest_process

logger = logging.getLogger(__name__)
base_url = os.getenv("CLI2REST_BPNET_URL", "http://localhost:8000")


def analyze(cif_content: str, **_: Dict[str, Any]) -> BaseInteractions:
    with TemporaryDirectory() as directory:
        input_file = os.path.join(directory, "input.cif")

        with open(input_file, "w") as f:
            f.write(cif_content)

        cli2rest_process(base_url, input_file, "bpnet/config-cif.yaml", directory)

        with open(input_file) as f:
            structure3d = read_3d_structure(f, None)

        return parse_external_output(
            [f"{directory}/input.rob", f"{directory}/input_basepair.json"],
            ExternalTool.BPNET,
            structure3d,
        )


def main():
    with open(sys.argv[1]) as f:
        structure = analyze(f.read())
    print(orjson.dumps(structure).decode("utf-8"))


if __name__ == "__main__":
    main()
