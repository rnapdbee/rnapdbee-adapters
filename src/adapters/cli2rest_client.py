from cli2rest_bio.cli2rest_bio import load_tool_config, process_file
from collections import namedtuple
from tempfile import TemporaryDirectory
import os
from typing import List, Optional, Dict
import logging

from rnapolis.adapter import parse_external_output, ExternalTool
from rnapolis.common import BaseInteractions
from rnapolis.parser import read_3d_structure


logger = logging.getLogger(__name__)


Arguments = namedtuple("Arguments", ["output_prefix_format", "no_auto_ungzip"])


# Possible values for tool:
# barnaba OR barnaba/config.yaml
# bpnet/config-cif.yaml
# bpnet/config-pdb.yaml
# dssr OR dssr/config.yaml
# fr3d OR fr3d/config.yaml
# maxit/config-cif2mmcif.yaml
# maxit/config-cif2pdb.yaml
# maxit/config-pdb2cif.yaml
# mc-annotate OR mc-annotate/config.yaml
# rchie OR rchie/config.yaml
# reduce OR reduce/config.yaml
# rnapolis/config-splitter.yaml
# rnapolis/config-unifier.yaml
# rnaview/config-cif.yaml
# rnaview/config-pdb.yaml
# varna-tz OR varna-tz/config.yaml
def _cli2rest_run_in_directory(base_url, input_file, tool, output_dir):
    config = load_tool_config(tool)
    tool_name = config["name"]
    args = Arguments(output_prefix_format="", no_auto_ungzip=True)
    process_file(input_file, config, args, base_url, tool_name, output_dir)


def cli2rest_run(
    base_url: str,
    input_file_content: str,
    input_file_extension: str,
    config_name: str,
    output_files: List[str],
) -> Dict[str, str]:
    with TemporaryDirectory() as directory:
        input_file = os.path.join(directory, f"input{input_file_extension}")

        with open(input_file, "w") as f:
            f.write(input_file_content)

        _cli2rest_run_in_directory(base_url, input_file, config_name, directory)

        result = {}
        missing_files = []
        for output_file in ["stdout.txt", "stderr.txt"] + output_files:
            output_path = os.path.join(directory, output_file)
            if os.path.exists(output_path):
                with open(output_path) as f:
                    result[output_file] = f.read()
            else:
                logger.warning("File %s not found", output_path)
                missing_files.append(output_file)

        if missing_files:
            print("stdout:", result.get("stdout.txt"))
            print("stderr:", result.get("stderr.txt"))

        return result


def cli2rest_analyze_structure(
    base_url: str,
    input_file_content: str,
    external_tool: ExternalTool,
    output_files: List[str],
    input_file_extension: str = ".cif",
    config_name: Optional[str] = None,
) -> BaseInteractions:
    with TemporaryDirectory() as directory:
        input_file = os.path.join(directory, f"input{input_file_extension}")

        with open(input_file, "w+") as f:
            f.write(input_file_content)
            f.seek(0)
            _cli2rest_run_in_directory(
                base_url, input_file, config_name or external_tool.value, directory
            )
            f.seek(0)
            structure3d = read_3d_structure(f, None)

        return parse_external_output(
            [f"{directory}/{output_file}" for output_file in output_files],
            external_tool,
            structure3d,
        )
