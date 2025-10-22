#! /usr/bin/env python
import logging
import os
import sys
from typing import Any, Dict

import orjson
from rnapolis.adapter import ExternalTool
from rnapolis.common import BaseInteractions

from adapters.cli2rest_client import cli2rest_analyze_structure


logger = logging.getLogger(__name__)
base_url = os.getenv("CLI2REST_DSSR_URL", "http://localhost:8000")


def analyze(file_content: str, **_: Dict[str, Any]) -> BaseInteractions:
    return cli2rest_analyze_structure(
        base_url,
        file_content,
        ExternalTool.DSSR,
        ["output.json"],
    )


def main():
    with open(sys.argv[1]) as f:
        structure = analyze(f.read())
    print(orjson.dumps(structure).decode("utf-8"))


if __name__ == "__main__":
    main()
