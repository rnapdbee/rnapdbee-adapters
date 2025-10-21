from cli2rest_bio.cli2rest_bio import load_tool_config, process_file
from collections import namedtuple

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
def cli2rest_process(base_url, input_file, tool, output_dir):
    config = load_tool_config(tool)
    tool_name = config["name"]
    args = Arguments(output_prefix_format="", no_auto_ungzip=True)
    process_file(input_file, config, args, base_url, tool_name, output_dir)
