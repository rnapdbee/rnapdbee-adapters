from typing import Callable

import orjson
from rnapolis.common import Structure2D

from adapters.tools import visualization_utils
from adapters.tools import output_filter, cif_filter, pdb_filter
from adapters.visualization.model import Model2D, ModelMulti2D


def run_cif_adapter(analyze: Callable[..., Structure2D], data: str, model: int) -> Structure2D:
    cif_content = cif_filter.apply(data, [
        (cif_filter.leave_single_model, {'model': model}),
        (cif_filter.remove_proteins, {}),
        (cif_filter.fix_occupancy, {}),
    ])

    analysis_output = analyze(cif_content, model=model)

    return output_filter.apply(analysis_output, [
        (output_filter.remove_duplicate_pairs, {}),
        (output_filter.sort_interactions_lists, {}),
    ])


def run_pdb_adapter(analyze: Callable[..., Structure2D], data: str, model: int) -> Structure2D:
    pdb_content = pdb_filter.apply(data, [
        (pdb_filter.leave_single_model, {'model': model}),
    ])

    mapped_content, mapped_chains = pdb_filter.replace_chains(pdb_content)

    analysis_output = analyze(mapped_content, model=model)

    return output_filter.apply(analysis_output, [
        (output_filter.restore_chains, {'mapped_chains': mapped_chains}),
        (output_filter.remove_duplicate_pairs, {}),
        (output_filter.sort_interactions_lists, {}),
    ])


def run_visualization_adapter(adapter, data: bytes) -> str:
    model = Model2D.from_dict(orjson.loads(data))
    model_with_unique_strands = visualization_utils.ensure_unique_strands(model)
    return adapter.visualize(model_with_unique_strands)


def run_multi_visualization_adapter(adapter, data: bytes) -> str:
    model = ModelMulti2D.from_dict(orjson.loads(data))
    model_with_unique_strands = visualization_utils.ensure_unique_strands_in_multi(model)
    return adapter.visualize(model_with_unique_strands)
