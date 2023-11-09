import logging
from typing import Dict, List

from adapters.visualization.model import (
    ChainWithResidues,
    Interaction,
    Model2D,
    ModelMulti2D,
    NonCanonicalInteractions,
    Residue,
    ResultMulti2D,
    Strand,
)

logger = logging.getLogger(__name__)


def ensure_unique_strands_in_multi(model: ModelMulti2D) -> ModelMulti2D:
    strands_names = [strand.name for strand in model.results[0].strands]
    unique_strands_names = set(strands_names)
    if len(strands_names) == len(unique_strands_names):
        return model

    logger.info("Duplicated strands detected - renaming started (model multi 2D)")
    results: List[ResultMulti2D] = []

    for result in model.results:
        counter: Dict[str, int] = {}
        strands: List[Strand] = []
        for strand in result.strands:
            counter[strand.name] = counter.get(strand.name, 0) + 1
            new_name = f"{strand.name}{counter[strand.name]}"
            strands.append(Strand(new_name, strand.sequence, strand.structure))
        results.append(ResultMulti2D(result.adapter, strands))

    return ModelMulti2D(results)


def ensure_unique_strands(model: Model2D) -> Model2D:
    strands_names = [strand.name for strand in model.strands]
    unique_strands_names = set(strands_names)
    if len(strands_names) == len(unique_strands_names):
        return model

    logger.info("Duplicated strands detected - renaming started (model 2D)")
    strands: List[Strand] = []
    counter: Dict[str, int] = {}
    for strand in model.strands:
        counter[strand.name] = counter.get(strand.name, 0) + 1
        new_name = f"{strand.name}{counter[strand.name]}"
        strands.append(Strand(new_name, strand.sequence, strand.structure))

    chains_with_residues: List[ChainWithResidues] = []
    counter: Dict[str, int] = {}
    for chain_with_residues in model.chainsWithResidues:
        counter[chain_with_residues.name] = counter.get(chain_with_residues.name, 0) + 1
        new_name = f"{chain_with_residues.name}{counter[chain_with_residues.name]}"
        residues: List[Residue] = []
        for residue in chain_with_residues.residues:
            residues.append(
                Residue(
                    new_name,
                    residue.number,
                    residue.name,
                    residue.icode,
                )
            )
        chains_with_residues.append(ChainWithResidues(new_name, residues))

    residues: List[Residue] = []
    for chain_with_residues in chains_with_residues:
        for residue in chain_with_residues.residues:
            residues.append(residue)

    not_represented: List[Interaction] = []
    for interaction in model.nonCanonicalInteractions.notRepresented:
        index_left = model.residues.index(interaction.residueLeft)
        index_right = model.residues.index(interaction.residueRight)
        not_represented.append(
            Interaction(
                residues[index_left],
                residues[index_right],
                interaction.leontisWesthof,
            )
        )

    represented: List[Interaction] = []
    for interaction in model.nonCanonicalInteractions.represented:
        index_left = model.residues.index(interaction.residueLeft)
        index_right = model.residues.index(interaction.residueRight)
        represented.append(
            Interaction(
                residues[index_left],
                residues[index_right],
                interaction.leontisWesthof,
            )
        )

    return Model2D(
        strands,
        residues,
        chains_with_residues,
        NonCanonicalInteractions(not_represented, represented),
    )
