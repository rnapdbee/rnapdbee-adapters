from typing import Callable

import orjson
from rnapolis.common import BaseInteractions

from adapters.tools import cif_filter, output_filter, pdb_filter, visualization_utils
from adapters.visualization.model import Model2D, ModelMulti2D


def run_cif_adapter(
    analyze: Callable[..., BaseInteractions], data: str, model: int
) -> BaseInteractions:
    cif_content = cif_filter.apply(
        data,
        [
            (cif_filter.leave_single_model, {"model": model}),
            (cif_filter.fix_occupancy, {}),
        ],
    )

    analysis_output = analyze(cif_content, model=model)

    return output_filter.apply(
        analysis_output,
        [
            (output_filter.remove_duplicate_pairs, {}),
            (output_filter.sort_interactions_lists, {}),
        ],
    )


def run_pdb_adapter(
    analyze: Callable[..., BaseInteractions], data: str, model: int
) -> BaseInteractions:
    result = pdb_filter.apply(
        data,
        [
            (cif_filter.leave_single_model, {"model": model}),
            (cif_filter.fix_occupancy, {}),
        ],
    )

    # If the result is None, it means that the input data is not representable as a valid PDB file
    if result is None:
        return BaseInteractions([], [], [], [], [])

    pdb_content, mapped_chains = result
    analysis_output = analyze(pdb_content, model=model)

    return output_filter.apply(
        analysis_output,
        [
            (output_filter.remove_duplicate_pairs, {}),
            (output_filter.restore_chains, {"mapped_chains": mapped_chains}),
            (output_filter.sort_interactions_lists, {}),
        ],
    )


def run_visualization_adapter(adapter, data: bytes) -> str:
    model = Model2D.from_dict(orjson.loads(data))
    model_with_unique_strands = visualization_utils.ensure_unique_strands(model)
    return adapter.visualize(model_with_unique_strands)


def run_multi_visualization_adapter(adapter, data: bytes) -> str:
    model = ModelMulti2D.from_dict(orjson.loads(data))
    model_with_unique_strands = visualization_utils.ensure_unique_strands_in_multi(
        model
    )
    return adapter.visualize(model_with_unique_strands)
