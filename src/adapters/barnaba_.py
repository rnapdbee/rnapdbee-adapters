#! /usr/bin/env python
# IMPORTANT! this file cannot be named barnaba.py, because it imports from "barnaba", and Python complains about that
import orjson
import barnaba
import tempfile
import sys

from typing import List, Optional, Tuple

from adapters.model import AnalysisOutput, BasePair, LeontisWesthof, OtherInteraction, \
    Residue, ResidueAuth, Stacking, StackingTopology


def residue_from_pair(resinfo: str, chain_ids: List[str]) -> Residue:
    resinfo = resinfo.split('_')
    # TODO: insertion code
    return Residue(None, ResidueAuth(chain_ids[int(resinfo[2])], int(resinfo[1]), '?', resinfo[0]))


def convert_interaction(interaction: str) -> Optional[LeontisWesthof]:
    # Unknown interaction
    if 'x' in interaction.lower():
        return None

    if interaction in ('WCc', 'GUc'):
        return LeontisWesthof['cWW']

    return LeontisWesthof[f'{interaction[2]}{interaction[:2]}']


def convert_stacking_topology(topology: str) -> StackingTopology:
    name = {'>>': 'upward', '<<': 'downward', '<>': 'outward', '><': 'inward'}[topology]
    return StackingTopology[name]


def parse_pdb(file_content: str) -> List[str]:
    chain_ids = []

    # Column 21 - chainID
    for line in file_content.splitlines():
        if line.startswith('ATOM') or line.startswith('HETATM'):
            if line[21] not in chain_ids:
                chain_ids.append(line[21])

    return chain_ids


def parse_barnaba(barnaba_result: Tuple[List[str], List[str], List[str]],
                  chain_ids: List[str]) -> Tuple[List[BasePair], List[Stacking], List[OtherInteraction]]:

    stackings, pairings, res = barnaba_result

    base_pairs = []
    base_stackings = []
    other_interactions = []

    for p, pairing in enumerate(pairings[0][0]):
        res1 = res[pairing[0]]
        res2 = res[pairing[1]]
        interaction = pairings[0][1][p]
        nt1 = residue_from_pair(res1, chain_ids)
        nt2 = residue_from_pair(res2, chain_ids)
        lw = convert_interaction(interaction)
        if lw is None:
            other_interactions.append(OtherInteraction(nt1, nt2))
        else:
            base_pairs.append(BasePair(nt1, nt2, lw, None))

    for s, stacking in enumerate(stackings[0][0]):
        res1 = res[stacking[0]]
        res2 = res[stacking[1]]
        interaction = stackings[0][1][s]
        nt1 = residue_from_pair(res1, chain_ids)
        nt2 = residue_from_pair(res2, chain_ids)
        topology = convert_stacking_topology(interaction)
        base_stackings.append(Stacking(nt1, nt2, topology))

    return base_pairs, base_stackings, other_interactions


def analyze(file_content: str) -> AnalysisOutput:
    directory = tempfile.TemporaryDirectory()

    with tempfile.NamedTemporaryFile('w+', dir=directory.name, suffix='.pdb') as file:
        file.write(file_content)
        file.seek(0)
        barnaba_result = barnaba.annotate(file.name)

    chain_ids = parse_pdb(file_content)
    parsed_output = parse_barnaba(barnaba_result, chain_ids)

    base_pairs, base_stackings, other_interactions = parsed_output
    return AnalysisOutput(base_pairs, base_stackings, [], [], other_interactions)


def main() -> None:
    structure = analyze(sys.stdin.read())
    print(orjson.dumps(structure).decode('utf-8'))


if __name__ == '__main__':
    main()
