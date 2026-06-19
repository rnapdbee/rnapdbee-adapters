import argparse
import logging
import os
from tempfile import TemporaryDirectory
from typing import List, Optional

import orjson
from cli2rest_bio.cli2rest_bio import load_tool_config, process_file
from rnapolis.adapter import ExternalTool, parse_external_output
from rnapolis.common import BaseInteractions
from rnapolis.parser import read_3d_structure

logger = logging.getLogger(__name__)


# Possible values for config_name:
# barnaba/config.yaml
# bpnet/config-cif.yaml
# bpnet/config-pdb.yaml
# dssr/config.yaml
# fr3d/config.yaml
# inkscape/config-svg2pdf-with-caption.yaml
# inkscape/config-svg2pdf.yaml
# inkscape/config-svg2png.yaml
# maxit/config-cif2mmcif.yaml
# maxit/config-cif2pdb.yaml
# maxit/config-pdb2cif.yaml
# mc-annotate/config.yaml
# rchie/config.yaml
# rnapuzzler/config.yaml
# reduce/config.yaml
# rnapolis/config-annotator.yaml
# rnapolis/config-coplanarity-checker.yaml
# rnapolis/config-splitter.yaml
# rnapolis/config-unifier.yaml
# rnaview/config-cif.yaml
# rnaview/config-pdb.yaml
# varna-tz/config.yaml
def _cli2rest_run(
    base_url: str,
    input_file_content: str,
    input_file_extension: str,
    config_name: str,
    directory: str,
    timeout: Optional[int] = None,
):
    input_file = os.path.join(directory, f"input{input_file_extension}")
    with open(input_file, "w") as f:
        f.write(input_file_content)

    config = load_tool_config(config_name)
    tool_name = config["name"]
    args = argparse.Namespace(
        output_prefix_format="",
        no_auto_ungzip=True,
        output_metadata=f"{directory}/metadata.json",
        timeout=timeout,
    )
    metadata = process_file(input_file, config, args, base_url, tool_name, directory)

    with open(f"{directory}/metadata.json", "wb") as f:
        f.write(orjson.dumps(metadata))
    logger.debug("Metadata:\n" + orjson.dumps(metadata).decode("utf-8"))

    with open(f"{directory}/stdout.txt", "w", encoding="utf-8") as f:
        f.write(metadata.get("stdout") or "")

    with open(f"{directory}/stderr.txt", "w", encoding="utf-8") as f:
        f.write(metadata.get("stderr") or "")


def _log_output_on_error(directory: str):
    for filename in ["stdout.txt", "stderr.txt"]:
        path = os.path.join(directory, filename)
        if os.path.exists(path):
            with open(path, "r") as f:
                content = f.read()
                if len(content) > 2000:
                    display = (
                        f"{content[:1000]}\n... [truncated] ...\n{content[-1000:]}"
                    )
                else:
                    display = content
                logger.error(f"Content of {filename}:\n{display}")


def cli2rest_run_single(
    base_url: str,
    input_file_content: str,
    input_file_extension: str,
    config_name: str,
    output_file: str,
    timeout: Optional[int] = None,
) -> str:
    with TemporaryDirectory() as directory:
        _cli2rest_run(
            base_url,
            input_file_content,
            input_file_extension,
            config_name,
            directory,
            timeout,
        )

        output_path = os.path.join(directory, output_file)
        if not os.path.exists(output_path):
            _log_output_on_error(directory)
            raise FileNotFoundError(f"Output file {output_file} not found")

        with open(output_path) as f:
            return f.read()


def cli2rest_analyze_structure(
    base_url: str,
    input_file_content: str,
    input_file_extension: str,
    config_name: str,
    external_tool: ExternalTool,
    output_files: List[str],
    timeout: Optional[str] = None,
) -> BaseInteractions:
    with TemporaryDirectory() as directory:
        _cli2rest_run(
            base_url,
            input_file_content,
            input_file_extension,
            config_name,
            directory,
            timeout,
        )

        input_file = os.path.join(directory, f"input{input_file_extension}")
        with open(input_file) as f:
            structure3d = read_3d_structure(f, None)

        output_paths: List[str] = []
        for output_file in output_files:
            output_path = os.path.join(directory, output_file)
            if not os.path.exists(output_path):
                _log_output_on_error(directory)
                raise FileNotFoundError(f"Output file {output_file} not found")
            output_paths.append(output_path)

        return parse_external_output(output_paths, external_tool, structure3d)
