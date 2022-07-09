#! /usr/bin/env python

import sys
import subprocess
import orjson
import tempfile

from typing import Dict, List
from enum import Enum

from adapters.model import AnalysisOutput, BasePair, BasePhosphate, BaseRibose, LeontisWesthof, \
    Residue, ResidueAuth, Saenger, Stacking, StackingTopology

PATH = './../../dev/'

BASE_EDGES = ('Ww', 'Bh', 'Hh', 'Bs', 'Ws')


class ParseState(str, Enum):
    residue = 'Residue conformations',
    adjacent = 'Adjacent stackings',
    non_adjacent = 'Non-Adjacent stackings',
    base_pairs = 'Base-pairs',
    number_of = 'Number of'


def get_residue(res_info: str, name: str) -> Residue:
    chainID = res_info[0]
    number_icode = res_info.split('.', 1)
    number = int(number_icode[0][1:])
    icode = '?' if len(number_icode) == 1 else number_icode[1]
    return Residue(None, ResidueAuth(chainID, number, icode, name))


def get_stacking(line: str, names: Dict[str, str], topology_pos: int) -> Stacking:
    splitted = line.split()
    topology_info = splitted[topology_pos]

    res1_info, res2_info = splitted[0].split('-', 1)
    name1, name2 = names[res1_info], names[res2_info]

    res1 = get_residue(res1_info, name1)
    res2 = get_residue(res2_info, name2)

    return Stacking(res1, res2, StackingTopology[topology_info])


def get_others(
    line: str,
    base_pairs: List[BasePair],
    base_ribose: List[BaseRibose],
    base_phosphate: List[BasePhosphate],
) -> None:
    splitted = line.split()

    res1_info, res2_info = splitted[0].split('-', 1)
    name1, name2 = splitted[2].split('-', 1)

    res1 = get_residue(res1_info, name1)
    res2 = get_residue(res2_info, name2)

    base_added, ribose_added, phosphate_added = False, False, False

    for type in splitted[3:]:
        if "O2'" in type and not ribose_added:
            if type.split('/', 1)[0] == "O2'":
                res1, res2 = res2, res1
            base_ribose.append(BaseRibose(res1, res2, None))
            ribose_added = True

        elif 'O2P' in type and not phosphate_added:
            if type.split('/', 1)[0] == 'O2P':
                res1, res2 = res2, res1
            base_phosphate.append(BasePhosphate(res1, res2, None))
            phosphate_added = True

        elif any(i in type.split('/', 1)[0] for i in BASE_EDGES) and any(
                i in type.split('/', 1)[1] for i in BASE_EDGES) and not base_added:
            cis_trans = splitted[-2][0]
            saenger = Saenger[splitted[-1]]
            lw_left = type.split("/", 1)[0][1].upper()
            lw_right = type.split("/", 1)[1][1].upper()
            lw = LeontisWesthof[f'{cis_trans}{lw_left}{lw_right}']
            base_pairs.append(BasePair(res1, res2, lw, saenger))
            base_added = True


def analyze(pdb_content: str) -> AnalysisOutput:

    directory = tempfile.TemporaryDirectory()
    with tempfile.NamedTemporaryFile('w+', dir=directory.name, suffix='.pdb') as file:
        file.write(pdb_content)
        file.seek(0)
        mc_result = subprocess.run(['mc-annotate', file.name], stdout=subprocess.PIPE,
                                   stderr=subprocess.DEVNULL).stdout.decode('utf-8')

    current_state = None
    names = {}

    base_pairs = []
    stackings = []
    base_ribose = []
    base_phosphate = []

    for line in mc_result.splitlines():

        for state in ParseState:
            if line.startswith(state.value):
                current_state = state
                break
        else:
            if current_state == ParseState.residue:
                splitted = line.split()
                chain, name = splitted[0], splitted[2]
                names[chain] = name
            elif current_state == ParseState.adjacent:
                stackings.append(get_stacking(line, names, 3))
            elif current_state == ParseState.non_adjacent:
                stackings.append(get_stacking(line, names, 2))
            elif current_state == ParseState.base_pairs:
                get_others(line, base_pairs, base_ribose, base_phosphate)

    return AnalysisOutput(base_pairs, stackings, base_ribose, base_phosphate, [])


def main() -> None:
    structure = analyze(sys.stdin.read())
    print(orjson.dumps(structure).decode('utf-8'))


if __name__ == '__main__':
    main()
