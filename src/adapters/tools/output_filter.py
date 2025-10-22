from typing import Callable, Dict, Iterable, List, Tuple, Type, TypeVar

from rnapolis.common import (
    BaseInteractions,
    BasePair,
    BasePhosphate,
    BaseRibose,
    Interaction,
    LeontisWesthof,
    OtherInteraction,
    Residue,
    ResidueAuth,
    ResidueLabel,
    Stacking,
    StackingTopology,
)

InteractionTypeT = TypeVar("InteractionTypeT", BasePair, Stacking, OtherInteraction)


def apply(
    analysis_output: BaseInteractions, functions_args: Iterable[Tuple[Callable, Dict]]
) -> BaseInteractions:
    for function, kwargs in functions_args:
        analysis_output = function(analysis_output, **kwargs)
    return analysis_output


def remove_duplicate_pairs(analysis_output: BaseInteractions, *_) -> BaseInteractions:
    stacking_topology_mapping = {
        StackingTopology.upward: StackingTopology.downward,
        StackingTopology.downward: StackingTopology.upward,
        StackingTopology.inward: StackingTopology.outward,
        StackingTopology.outward: StackingTopology.inward,
        None: None,
    }

    def reverse_base_interaction(interaction: BasePair) -> BasePair:
        old_lw = interaction.lw.name
        lw = LeontisWesthof[f"{old_lw[0]}{old_lw[2]}{old_lw[1]}"]
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

    filtered_base_pairs = remove_duplicate_pairs_from_list(
        analysis_output.base_pairs, reverse_base_interaction
    )
    filtered_stackings = remove_duplicate_pairs_from_list(
        analysis_output.stackings, reverse_stacking_interaction
    )
    filtered_other_interactions = remove_duplicate_pairs_from_list(
        analysis_output.other_interactions,
        reverse_other_interaction,
    )

    return BaseInteractions(
        filtered_base_pairs,
        filtered_stackings,
        analysis_output.base_ribose_interactions,
        analysis_output.base_phosphate_interactions,
        filtered_other_interactions,
    )


def sort_interactions_lists(analysis_output: BaseInteractions, *_) -> BaseInteractions:
    interactions_list: List[Type[Interaction]]
    for interactions_list in [
        analysis_output.base_pairs,
        analysis_output.stackings,
        analysis_output.base_ribose_interactions,
        analysis_output.base_phosphate_interactions,
        analysis_output.other_interactions,
    ]:
        interactions_list.sort(
            key=lambda pair: (
                pair.nt1.chain,
                pair.nt1.number,
                pair.nt1.icode or "",
                pair.nt2.chain,
                pair.nt2.number,
                pair.nt2.icode or "",
            )
        )

    return analysis_output


def restore_chains(analysis_output: BaseInteractions, **kwargs) -> BaseInteractions:
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

    mapped_chains: Dict[str, str] = kwargs.get("mapped_chains", {})

    base_pairs: List[BasePair] = []
    stackings: List[Stacking] = []
    base_riboses: List[BaseRibose] = []
    base_phosphates: List[BasePhosphate] = []
    other_interactions: List[OtherInteraction] = []

    for base_pair in analysis_output.base_pairs:
        base_pairs.append(
            BasePair(
                map_residue(base_pair.nt1, mapped_chains),
                map_residue(base_pair.nt2, mapped_chains),
                base_pair.lw,
                base_pair.saenger,
            )
        )

    for stacking in analysis_output.stackings:
        stackings.append(
            Stacking(
                map_residue(stacking.nt1, mapped_chains),
                map_residue(stacking.nt2, mapped_chains),
                stacking.topology,
            )
        )

    for base_ribose in analysis_output.base_ribose_interactions:
        base_riboses.append(
            BaseRibose(
                map_residue(base_ribose.nt1, mapped_chains),
                map_residue(base_ribose.nt2, mapped_chains),
                base_ribose.br,
            )
        )

    for base_phosphate in analysis_output.base_phosphate_interactions:
        base_phosphates.append(
            BasePhosphate(
                map_residue(base_phosphate.nt1, mapped_chains),
                map_residue(base_phosphate.nt2, mapped_chains),
                base_phosphate.bph,
            )
        )

    for other_interaction in analysis_output.other_interactions:
        other_interactions.append(
            OtherInteraction(
                map_residue(other_interaction.nt1, mapped_chains),
                map_residue(other_interaction.nt2, mapped_chains),
            )
        )

    return BaseInteractions(
        base_pairs, stackings, base_riboses, base_phosphates, other_interactions
    )
