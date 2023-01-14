#! /usr/bin/env python
# IMPORTANT! this file cannot be named fr3d.py, because it imports from "fr3d", and Python complains about that
import io
import os
import sys
import logging
from typing import Tuple, Dict, Any

import orjson
from fr3d.cif.reader import Cif
from fr3d.classifiers import NA_pairwise_interactions as interactions
from rnapolis.common import (
    BasePair,
    BasePhosphate,
    BaseRibose,
    LeontisWesthof,
    OtherInteraction,
    Residue,
    ResidueAuth,
    Stacking,
    StackingTopology,
    Structure2D,
)

logger = logging.getLogger(__name__)

SCREEN_DISTANCE_CUTOFF = 12


def parse_unit_id(nt: str) -> Residue:
    fields = nt.split('|')
    icode = fields[7] if len(fields) >= 8 and fields[7] != '' else None
    auth = ResidueAuth(fields[2], int(fields[4]), icode, fields[3])
    return Residue(None, auth)


def parse_unit_ids(pair: Tuple) -> Tuple[Residue, Residue]:
    nt1, nt2, _ = pair
    return parse_unit_id(nt1), parse_unit_id(nt2)


def unify_classification(fr3d_name: str) -> Tuple:
    name = fr3d_name.replace('_exp', '')
    name = name[1:] if name.startswith('n') else name
    name = name[1:] if name.startswith('a') else name

    if name == 's33':
        return ('stacking', StackingTopology.downward)
    if name == 's55':
        return ('stacking', StackingTopology.upward)
    if name == 's35':
        return ('stacking', StackingTopology.outward)
    if name == 's53':
        return ('stacking', StackingTopology.inward)
    if name in ("s3O2'", "s3O3'", "s3O4'"):
        return ('base-ribose', None)
    if name in ("s3O5'", "s3OP1", "s3OP2"):
        return ('base-phosphate', None)
    if len(name) == 3:
        try:
            name = 'tHS' if name.lower() == 'hts' else name  # typo?
            name = f'{name[0].lower()}{name[1].upper()}{name[2].upper()}'
            return ('base-pair', LeontisWesthof[name])
        except KeyError:
            logger.debug(f'Fr3d unknown interaction: {fr3d_name}')
    return ('other', None)


def analyze(file_content: str, **_: Dict[str, Any]) -> Structure2D:
    with open(os.devnull, 'w', encoding='utf-8') as devnull:
        original_stdout = sys.stdout
        sys.stdout = devnull
        structure = Cif(io.StringIO(file_content)).structure()
        interaction_map, _, _, _ = interactions.annotate_nt_nt_in_structure(structure, {
            'stacking': [],
            'coplanar': [],
        })
        sys.stdout = original_stdout
        logger.debug(f'fr3d interaction map: {interaction_map}')

    base_pairs = []
    stackings = []
    base_ribose_interactions = []
    base_phosphate_interactions = []
    other_interactions = []

    for key, value_list in interaction_map.items():
        for value in value_list:
            nt1, nt2 = parse_unit_ids(value)
            x, classification = unify_classification(key)
            if x == 'base-pair':
                base_pairs.append(BasePair(nt1, nt2, classification, None))
            if x == 'stacking':
                stackings.append(Stacking(nt1, nt2, classification))
            if x == 'base-ribose':
                base_ribose_interactions.append(BaseRibose(nt1, nt2, classification))
            if x == 'base-phosphate':
                base_phosphate_interactions.append(BasePhosphate(nt1, nt2, classification))
            if x == 'other':
                other_interactions.append(OtherInteraction(nt1, nt2))

    return Structure2D(base_pairs, stackings, base_ribose_interactions, base_phosphate_interactions, other_interactions)


def main():
    result = analyze(sys.stdin.read())
    print(orjson.dumps(result).decode('utf-8'))


if __name__ == '__main__':
    main()
