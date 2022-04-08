#! /usr/bin/env python
import io
import orjson
import os
import sys

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple

from fr3d.cif.reader import Cif
from fr3d.classifiers import NA_pairwise_interactions as interactions

SCREEN_DISTANCE_CUTOFF = 12


class LeontisWesthof(Enum):
    cWW = 'cWW'
    cWH = 'cWH'
    cWS = 'cWS'
    cHW = 'cHW'
    cHH = 'cHH'
    cHS = 'cHS'
    cSW = 'cSW'
    cSH = 'cSH'
    cSS = 'cSS'
    tWW = 'tWW'
    tWH = 'tWH'
    tWS = 'tWS'
    tHW = 'tHW'
    tHH = 'tHH'
    tHS = 'tHS'
    tSW = 'tSW'
    tSH = 'tSH'
    tSS = 'tSS'


class StackingTopology(Enum):
    upward = 'upward'
    downward = 'downward'
    inward = 'inward'
    outward = 'outward'


# TODO
class BR(Enum):
    unknown = 'unknown'


# TODO
class BPh(Enum):
    unknown = 'unknown'


@dataclass
class Residue:
    chain: str
    number: int
    icode: Optional[str]
    name: str


@dataclass
class Interaction:
    nt1: Residue
    nt2: Residue


@dataclass
class BasePair(Interaction):
    lw: LeontisWesthof


@dataclass
class Stacking(Interaction):
    topology: StackingTopology


@dataclass
class BaseRibose(Interaction):
    br: BR


@dataclass
class BasePhosphate(Interaction):
    bph: BPh


@dataclass
class AnalysisOutput:
    basePairs: List[BasePair]
    stackings: List[Stacking]
    baseRiboseInteractions: List[BaseRibose]
    basePhosphateInteractions: List[BasePhosphate]


def parse_unit_id(nt: str) -> Residue:
    fields = nt.split('|')
    return Residue(fields[2], int(fields[4]), fields[8] if len(fields) >= 9 else None, fields[3])


def parse_unit_ids(pair: Tuple) -> Tuple[Residue, Residue]:
    nt1, nt2 = pair
    return (parse_unit_id(nt1), parse_unit_id(nt2))


def unify_classification(fr3d_names: List[str]) -> Tuple:
    lw = set()
    stacking = set()
    base_ribose = set()
    base_phosphate = set()

    for name in fr3d_names:
        name = name.replace('_exp', '')
        name = name[1:] if name.startswith('n') else name
        name = name[1:] if name.startswith('a') else name

        if name == 's33':
            stacking.add(StackingTopology.downward)
        elif name == 's55':
            stacking.add(StackingTopology.upward)
        elif name == 's35':
            stacking.add(StackingTopology.outward)
        elif name == 's53':
            stacking.add(StackingTopology.inward)
        elif name in ("s3O2'", "s3O3'", "s3O4'"):
            base_ribose.add(BR.unknown)
        elif name in ("s3O5'", "s3OP1", "s3OP2"):
            base_phosphate.add(BR.unknown)
        else:
            assert len(name) == 3, name
            name = 'tHS' if name.lower() == 'hts' else name  # typo?
            name = f'{name[0].lower()}{name[1].upper()}{name[2].upper()}'
            lw.add(LeontisWesthof[name])
    return (lw, stacking, base_ribose, base_phosphate)


if __name__ == '__main__':
    with open(os.devnull, 'w') as devnull:
        content = sys.stdin.read()

        original_stdout = sys.stdout
        sys.stdout = devnull

        structure = Cif(io.StringIO(content)).structure()
        bases = structure.residues(type=["RNA linking", "DNA linking"])
        cubes, neighbours = interactions.make_nt_cubes(bases, SCREEN_DISTANCE_CUTOFF)
        interaction_to_triple_list, pair_to_interaction, list_nt_nt, _ = interactions.annotate_nt_nt_interactions(
            bases, SCREEN_DISTANCE_CUTOFF, cubes, neighbours, {})

        sys.stdout = original_stdout

        base_pairs = []
        stackings = []
        base_ribose_interactions = []
        base_phosphate_interactions = []

        for key, value in pair_to_interaction.items():
            nt1, nt2 = parse_unit_ids(key)
            lw, stacking, br, bph = unify_classification(value)
            for x in lw:
                base_pairs.append(BasePair(nt1, nt2, x))
            for x in stacking:
                stackings.append(Stacking(nt1, nt2, x))
            for x in br:
                base_ribose_interactions.append(BaseRibose(nt1, nt2, x))
            for x in bph:
                base_phosphate_interactions.append(BasePhosphate(nt1, nt2, x))

        result = AnalysisOutput(base_pairs, stackings, base_ribose_interactions, base_phosphate_interactions)
        print(orjson.dumps(result).decode('utf-8'))