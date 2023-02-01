from typing import Callable, Dict, Iterable, List, Tuple, TypeVar, Type

from rnapolis.common import (
    BasePair,
    LeontisWesthof,
    OtherInteraction,
    Stacking,
    StackingTopology,
    Structure2D,
    Interaction,
    Residue,
    ResidueAuth,
    ResidueLabel,
    BasePhosphate,
    BaseRibose,
)

InteractionTypeT = TypeVar('InteractionTypeT', BasePair, Stacking, OtherInteraction)


def apply(analysis_output: Structure2D, functions_args: Iterable[Tuple[Callable, Dict]]) -> Structure2D:

    for function, kwargs in functions_args:
        analysis_output = function(analysis_output, **kwargs)

    return analysis_output


def remove_duplicate_pairs(analysis_output: Structure2D, *_) -> Structure2D:
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
        interactions: List[InteractionTypeT],
        reverse_interaction: Callable[[InteractionTypeT], InteractionTypeT],
    ) -> List[InteractionTypeT]:
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

    return Structure2D(
        filtered_base_pairs,
        filtered_stackings,
        analysis_output.baseRiboseInteractions,
        analysis_output.basePhosphateInteractions,
        filtered_other_interactions,
    )


def sort_interactions_lists(analysis_output: Structure2D, *_) -> Structure2D:
    interactions_list: List[Type[Interaction]]
    for interactions_list in analysis_output.__dict__.values():
        interactions_list.sort(key=lambda pair: (
            pair.nt1.chain,
            pair.nt1.number,
            pair.nt2.chain,
            pair.nt2.number,
        ))

    return analysis_output


def restore_chains(analysis_output: Structure2D, **kwargs) -> Structure2D:

    def map_residue(res: Residue, mapped_chains: Dict[str, str]):
        if res.label is None:
            label = None
        else:
            label = ResidueLabel(
                mapped_chains[res.label.chain],
                res.label.number,
                res.label.name,
            )

        if res.auth is None:
            auth = None
        else:
            auth = ResidueAuth(
                mapped_chains[res.auth.chain],
                res.auth.number,
                res.auth.icode,
                res.auth.name,
            )

        return Residue(label, auth)

    mapped_chains: Dict[str, str] = kwargs.get('mapped_chains')

    base_pairs: List[BasePair] = []
    stackings: List[Stacking] = []
    base_riboses: List[BaseRibose] = []
    base_phosphates: List[BasePhosphate] = []
    other_interactions: List[OtherInteraction] = []

    for base_pair in analysis_output.basePairs:
        base_pairs.append(
            BasePair(
                map_residue(base_pair.nt1, mapped_chains),
                map_residue(base_pair.nt2, mapped_chains),
                base_pair.lw,
                base_pair.saenger,
            ))

    for stacking in analysis_output.stackings:
        stackings.append(
            Stacking(
                map_residue(stacking.nt1, mapped_chains),
                map_residue(stacking.nt2, mapped_chains),
                stacking.topology,
            ))

    for base_ribose in analysis_output.baseRiboseInteractions:
        base_riboses.append(
            BaseRibose(
                map_residue(base_ribose.nt1, mapped_chains),
                map_residue(base_ribose.nt2, mapped_chains),
                base_ribose.br,
            ))

    for base_phosphate in analysis_output.basePhosphateInteractions:
        base_phosphates.append(
            BasePhosphate(
                map_residue(base_phosphate.nt1, mapped_chains),
                map_residue(base_phosphate.nt2, mapped_chains),
                base_phosphate.bph,
            ))

    for other_interaction in analysis_output.otherInteractions:
        other_interactions.append(
            OtherInteraction(
                map_residue(other_interaction.nt1, mapped_chains),
                map_residue(other_interaction.nt2, mapped_chains),
            ))

    return Structure2D(base_pairs, stackings, base_riboses, base_phosphates, other_interactions)
