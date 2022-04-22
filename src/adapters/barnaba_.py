#! /usr/bin/env python
# IMPORTANT! this file cannot be named barnaba.py, because it imports from "barnaba", and Python complains about that
from lib2to3.pytree import Base
from traceback import StackSummary
import orjson
import barnaba
import tempfile
import sys

from typing import List

from adapters.model import AnalysisOutput, BasePair, BasePhosphate, BaseRibose, LeontisWesthof, \
    Residue, ResidueAuth, Stacking, StackingTopology

from adapters.utils import is_cif
from adapters.maxit import cif2pdb


def residue_from_pair(resinfo: str) -> Residue:
    resinfo = resinfo.split('_')
    # TODO: insertion code and chain
    return Residue(None, ResidueAuth('A', int(resinfo[1]), '?', resinfo[0]))


def convert_lw(interaction: str) -> LeontisWesthof:
    if interaction in ('WCc', 'GUc'):
        return LeontisWesthof['cWW']

    return LeontisWesthof[f'{interaction[2]}{interaction[:2]}']


def parse_base_pairs(pairings: List[str], res: List[str]) -> List[BasePair]:
    base_pairs = []

    for p in range(len(pairings[0][0])):
        res1 = res[pairings[0][0][p][0]]
        res2 = res[pairings[0][0][p][1]]
        interaction = pairings[0][1][p]
        nt1 = residue_from_pair(res1)
        nt2 = residue_from_pair(res2)
        lw = convert_lw(interaction)
        base_pairs.append(BasePair(nt1, nt2, lw, None))

    return base_pairs


def convert_stacking_topology(topology: str) -> StackingTopology:
    name = {'>>': 'upward', '<<': 'downward', '<>': 'outward', '><': 'inward'}[topology]
    return StackingTopology[name]


def parse_base_stackings(stackings: List[str], res: List[str]) -> List[Stacking]:
    base_stackings = []

    for p in range(len(stackings[0][0])):
        res1 = res[stackings[0][0][p][0]]
        res2 = res[stackings[0][0][p][1]]
        interaction = stackings[0][1][p]
        nt1 = residue_from_pair(res1)
        nt2 = residue_from_pair(res2)
        topology = convert_stacking_topology(interaction)
        base_stackings.append(Stacking(nt1, nt2, topology))

    return base_stackings


def analyze(file_content: str) -> AnalysisOutput:
    pdb_content = cif2pdb(file_content) if is_cif(file_content) else file_content
    suffix = '.pdb'

    directory = tempfile.TemporaryDirectory()
    file = tempfile.NamedTemporaryFile('w+', dir=directory.name, suffix=suffix)
    filename = file.name
    file.write(pdb_content)
    file.seek(0)

    stackings, pairings, res = barnaba.annotate(filename)

    base_pairs = parse_base_pairs(pairings, res)
    base_stackings = parse_base_stackings(stackings, res)

    file.close()
    return AnalysisOutput(base_pairs, base_stackings, None, None, None)


def main():
    structure = analyze(sys.stdin.read())
    print(orjson.dumps(structure).decode('utf-8'))


if __name__ == '__main__':
    main()
