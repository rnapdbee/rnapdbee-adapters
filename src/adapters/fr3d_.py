#! /usr/bin/env python
# IMPORTANT! this file cannot be named fr3d.py, because it imports from "fr3d", and Python complains about that
import io
import os
import sys
from typing import List, Tuple

import orjson
from fr3d.cif.reader import Cif
from fr3d.classifiers import NA_pairwise_interactions as interactions

from adapters.model import AnalysisOutput
from rnapolis.common import LeontisWesthof, BasePair, BasePhosphate, BaseRibose, \
    Residue, ResidueAuth, Stacking, StackingTopology

SCREEN_DISTANCE_CUTOFF = 12


def parse_unit_id(nt: str) -> Residue:
    fields = nt.split('|')
    auth = ResidueAuth(fields[2], int(fields[4]), fields[7] if len(fields) >= 8 else None, fields[3])
    return Residue(None, auth)


def parse_unit_ids(pair: Tuple) -> Tuple[Residue, Residue]:
    nt1, nt2 = pair
    return parse_unit_id(nt1), parse_unit_id(nt2)


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
            base_ribose.add(None)
        elif name in ("s3O5'", "s3OP1", "s3OP2"):
            base_phosphate.add(None)
        else:
            assert len(name) == 3, name
            name = 'tHS' if name.lower() == 'hts' else name  # typo?
            name = f'{name[0].lower()}{name[1].upper()}{name[2].upper()}'
            lw.add(LeontisWesthof[name])
    return lw, stacking, base_ribose, base_phosphate


def analyze(file_content: str) -> AnalysisOutput:
    with open(os.devnull, 'w', encoding='utf-8') as devnull:
        original_stdout = sys.stdout
        sys.stdout = devnull

        structure = Cif(io.StringIO(file_content)).structure()
        bases = structure.residues(type=["RNA linking", "DNA linking"])
        cubes, neighbours = interactions.make_nt_cubes(bases, SCREEN_DISTANCE_CUTOFF)
        _, pair_to_interaction, _, _ = interactions.annotate_nt_nt_interactions(bases, SCREEN_DISTANCE_CUTOFF, cubes,
                                                                                neighbours, {}, {})

        sys.stdout = original_stdout

    base_pairs = []
    stackings = []
    base_ribose_interactions = []
    base_phosphate_interactions = []

    for key, value in pair_to_interaction.items():
        nt1, nt2 = parse_unit_ids(key)
        lw, stacking, br, bph = unify_classification(value)
        for x in lw:
            base_pairs.append(BasePair(nt1, nt2, x, None))
        for x in stacking:
            stackings.append(Stacking(nt1, nt2, x))
        for x in br:
            base_ribose_interactions.append(BaseRibose(nt1, nt2, x))
        for x in bph:
            base_phosphate_interactions.append(BasePhosphate(nt1, nt2, x))

    return AnalysisOutput(base_pairs, stackings, base_ribose_interactions, base_phosphate_interactions, [])


def main():
    result = analyze(sys.stdin.read())
    print(orjson.dumps(result).decode('utf-8'))


if __name__ == '__main__':
    main()
