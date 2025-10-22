#! /usr/bin/env python
import logging
import os
import sys
from typing import Any, Dict

import orjson
from rnapolis.adapter import ExternalTool
from rnapolis.common import BaseInteractions

from adapters.analysis.generic import cli2rest_analyze

logger = logging.getLogger(__name__)
base_url = os.getenv("CLI2REST_BARNABA_URL", "http://localhost:8000")


def analyze(file_content: str, **_: Dict[str, Any]) -> BaseInteractions:
    return cli2rest_analyze(
        base_url,
        file_content,
        ExternalTool.BARNABA,
        ["outfile.ANNOTATE.pairing.out", "outfile.ANNOTATE.stacking.out"],
        extension=".pdb",
    )


def main():
    with open(sys.argv[1]) as f:
        structure = analyze(f.read())
    print(orjson.dumps(structure).decode("utf-8"))


if __name__ == "__main__":
    main()
