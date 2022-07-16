#! /usr/bin/env python

import sys
import subprocess
import orjson
import tempfile

from typing import Dict, List, Tuple
from enum import Enum

from adapters.model import AnalysisOutput, BasePair, BasePhosphate, BaseRibose, LeontisWesthof, \
    Residue, ResidueAuth, Saenger, Stacking, StackingTopology

BASE_EDGES = ('Hh', 'Hw', 'Bh', 'C8', 'Wh', 'Ww', 'Ws', 'Ss', 'Sw', 'Bs')


class ParseState(str, Enum):
    residue = 'Residue conformations',
    adjacent = 'Adjacent stackings',
    non_adjacent = 'Non-Adjacent stackings',
    base_pairs = 'Base-pairs',
    number_of = 'Number of'


def classify(type: str) -> str:
    if type in ('Hh', 'Hw', 'Bh', 'C8'):
        return 'H'
    if type in ('Wh', 'Ww', 'Ws'):
        return 'W'
    if type in ('Ss', 'Sw', 'Bs'):
        return 'S'
    raise ValueError('Type "{type}" unknown')


def get_residues(res_info: str, names: Dict[str, str]) -> Tuple[Residue, Residue]:
    chainID1 = res_info[0]
    tail = res_info[1:]

    if tail[0] == '-':
        tail1, res2_info = tail.split('-', 2)[1:]
        tail1 = '-' + tail1
        number1_icode1 = tail1.split('.', 1)
    else:
        tail1, res2_info = tail.split('-', 1)
        number1_icode1 = tail1.split('.', 1)

    res1_info = f'{chainID1}{tail1}'
    number1 = int(number1_icode1[0])
    icode1 = '?' if len(number1_icode1) == 1 else number1_icode1[1]
    res1 = Residue(None, ResidueAuth(chainID1, number1, icode1, names[res1_info]))

    chainID2 = res2_info[0]
    number2_icode2 = res2_info[1:].split('.', 1)
    number2 = int(number2_icode2[0])
    icode2 = '?' if len(number2_icode2) == 1 else number2_icode2[1]
    res2 = Residue(None, ResidueAuth(chainID2, number2, icode2, names[res2_info]))

    return res1, res2


def get_stacking(line: str, names: Dict[str, str], topology_pos: int) -> Stacking:
    splitted = line.split()
    topology_info = splitted[topology_pos]

    res1, res2 = get_residues(splitted[0], names)
    return Stacking(res1, res2, StackingTopology[topology_info])


def get_others(
    line: str,
    names: Dict[str, str],
    base_pairs: List[BasePair],
    base_ribose: List[BaseRibose],
    base_phosphate: List[BasePhosphate],
) -> None:
    splitted = line.split()

    res1, res2 = get_residues(splitted[0], names)

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

            if 'cis' in splitted[3:]:
                cis_trans = 'c'
            elif 'trans' in splitted[3:]:
                cis_trans = 't'
            else:
                raise ValueError(f'Cis/trans expected, but not present in {line}')

            if not all(char in ('I', 'V', 'X') for char in splitted[-1]):
                saenger = None
            else:
                saenger = Saenger[splitted[-1]]

            left, right = type.split("/", 1)
            lw_left, lw_right = classify(left), classify(right)
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
                get_others(line, names, base_pairs, base_ribose, base_phosphate)

    return AnalysisOutput(base_pairs, stackings, base_ribose, base_phosphate, [])


def main() -> None:
    structure = analyze(sys.stdin.read())
    print(orjson.dumps(structure).decode('utf-8'))


if __name__ == '__main__':
    main()
