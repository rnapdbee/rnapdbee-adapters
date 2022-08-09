from typing import Tuple, Iterable, Callable, Dict, List, TypeVar
from adapters.model import AnalysisOutput, BasePair, \
    LeontisWesthof, OtherInteraction, Stacking, StackingTopology

INTERACTION_TYPE = TypeVar('INTERACTION_TYPE', BasePair, Stacking, OtherInteraction)


def apply(analysis_output: AnalysisOutput, functions_args: Iterable[Tuple[Callable, Dict]]) -> AnalysisOutput:

    for f, kwargs in functions_args:
        analysis_output = f(analysis_output, **kwargs)

    return analysis_output


def remove_duplicate_pairs(analysis_output: AnalysisOutput, *_) -> AnalysisOutput:
    stacking_topology_mapping = {
        StackingTopology.upward: StackingTopology.downward,
        StackingTopology.downward: StackingTopology.upward,
        StackingTopology.inward: StackingTopology.outward,
        StackingTopology.outward: StackingTopology.inward,
        None: None,
    }

    def reverse_base_interaction(interaction: BasePair) -> BasePair:
        old_lw = interaction.lw.name
        lw = LeontisWesthof[f'{old_lw[0]}{old_lw[2]}{old_lw[1]}']
        return BasePair(interaction.nt2, interaction.nt1, lw, interaction.saenger)

    def reverse_stacking_interaction(interaction: Stacking) -> Stacking:
        topology = stacking_topology_mapping[interaction.topology]
        return Stacking(interaction.nt2, interaction.nt1, topology)

    def reverse_other_interaction(interaction: OtherInteraction) -> OtherInteraction:
        return OtherInteraction(interaction.nt2, interaction.nt1)

    def remove_duplicate_pairs_from_list(
        interactions: List[INTERACTION_TYPE],
        reverse_interaction: Callable[[INTERACTION_TYPE], INTERACTION_TYPE],
    ) -> List[INTERACTION_TYPE]:
        unique_interactions = {}
        for interaction in interactions:
            if interaction.nt1 < interaction.nt2:
                unique_interactions[str(interaction)] = interaction
            else:
                reversed_interaction = reverse_interaction(interaction)
                unique_interactions[str(reversed_interaction)] = reversed_interaction
        return list(unique_interactions.values())

    filtered_base_pairs = remove_duplicate_pairs_from_list(analysis_output.basePairs, reverse_base_interaction)
    filtered_stackings = remove_duplicate_pairs_from_list(analysis_output.stackings, reverse_stacking_interaction)
    filtered_other_interactions = remove_duplicate_pairs_from_list(
        analysis_output.otherInteractions,
        reverse_other_interaction,
    )

    return AnalysisOutput(
        filtered_base_pairs,
        filtered_stackings,
        analysis_output.baseRiboseInteractions,
        analysis_output.basePhosphateInteractions,
        filtered_other_interactions,
    )
