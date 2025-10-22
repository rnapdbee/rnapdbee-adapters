import logging
import os
from tempfile import TemporaryDirectory
from typing import List, Optional

from rnapolis.adapter import parse_external_output, ExternalTool
from rnapolis.common import BaseInteractions
from rnapolis.parser import read_3d_structure

from adapters.cli2rest_client import cli2rest_process

logger = logging.getLogger(__name__)


def cli2rest_analyze(
    base_url: str,
    file_content: str,
    external_tool: ExternalTool,
    output_files: List[str],
    extension: str = ".cif",
    config_name: Optional[str] = None,
) -> BaseInteractions:
    with TemporaryDirectory() as directory:
        input_file = os.path.join(directory, f"input{extension}")

        with open(input_file, "w") as f:
            f.write(file_content)

        cli2rest_process(
            base_url, input_file, config_name or external_tool.value, directory
        )

        with open(input_file) as f:
            structure3d = read_3d_structure(f, None)

        return parse_external_output(
            [f"{directory}/{output_file}" for output_file in output_files],
            external_tool,
            structure3d,
        )
