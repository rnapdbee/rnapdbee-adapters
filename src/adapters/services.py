from typing import Callable

from rnapolis.common import Structure2D

from adapters.tools import output_filter, cif_filter, pdb_filter


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

    analysis_output = analyze(pdb_content, model=model)

    return output_filter.apply(analysis_output, [
        (output_filter.remove_duplicate_pairs, {}),
        (output_filter.sort_interactions_lists, {}),
    ])
