#! /usr/bin/env python
# IMPORTANT! this file cannot be named barnaba.py, because it imports from "barnaba", and Python complains about that
import orjson
import barnaba
import tempfile
import sys

from typing import List, Optional, Tuple, Dict
from collections import defaultdict

from adapters.model import AnalysisOutput, BasePair, LeontisWesthof, OtherInteraction, \
    Residue, ResidueAuth, Stacking, StackingTopology


def residue_from_pair(
    resinfo: str,
    mapped_values: Tuple[List[str], Dict[str, Dict[int, Tuple[int, str]]]],
) -> Residue:
    resinfo_array = resinfo.split('_')
    chain_ids, mapped_numbers = mapped_values

    chain_id = chain_ids[int(resinfo_array[2])]
    name = resinfo_array[0]
    mapped_number = int(resinfo_array[1])
    number, icode = mapped_numbers[chain_id][mapped_number]
    icode = '?' if icode == '' else icode

    return Residue(None, ResidueAuth(chain_id, number, icode, name))


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

    # Column 21 - chainID (Character)
    for line in file_content.splitlines():
        if line.startswith('ATOM') or line.startswith('HETATM'):
            if line[21] not in chain_ids:
                chain_ids.append(line[21])

    return chain_ids


def parse_barnaba(
    barnaba_result: Tuple[List[str], List[str], List[str]],
    mapped_values: Tuple[List[str], Dict[str, Dict[int, Tuple[int, str]]]],
) -> Tuple[List[BasePair], List[Stacking], List[OtherInteraction]]:

    stackings, pairings, res = barnaba_result

    base_pairs = []
    base_stackings = []
    other_interactions = []

    for p, pairing in enumerate(pairings[0][0]):
        res1 = res[pairing[0]]
        res2 = res[pairing[1]]
        interaction = pairings[0][1][p]
        nt1 = residue_from_pair(res1, mapped_values)
        nt2 = residue_from_pair(res2, mapped_values)
        lw = convert_interaction(interaction)
        if lw is None:
            other_interactions.append(OtherInteraction(nt1, nt2))
        else:
            base_pairs.append(BasePair(nt1, nt2, lw, None))

    for s, stacking in enumerate(stackings[0][0]):
        res1 = res[stacking[0]]
        res2 = res[stacking[1]]
        interaction = stackings[0][1][s]
        nt1 = residue_from_pair(res1, mapped_values)
        nt2 = residue_from_pair(res2, mapped_values)
        topology = convert_stacking_topology(interaction)
        base_stackings.append(Stacking(nt1, nt2, topology))

    return base_pairs, base_stackings, other_interactions


def renumber_pdb(file_content: str) -> Tuple[str, Dict[str, Dict[int, Tuple[int, str]]]]:
    new_numbers = defaultdict(int)
    mapped_numbers = defaultdict(dict)

    renum_arr = []

    # Column 21 - chainID (Character)
    # Column 22-25 - resSeq (Integer)
    # Column 26 - iCode (Character)

    for line in file_content.splitlines(True):
        new_line = ''

        if line.startswith('ATOM') or line.startswith('HETATM'):
            old_number = int(line[22:26].strip())
            icode = line[26].strip()
            chain_id = line[21].strip()

            if (old_number, icode) not in mapped_numbers[chain_id].values():
                new_numbers[chain_id] += 1
                mapped_numbers[chain_id][new_numbers[chain_id]] = (old_number, icode)

            new_line = f'{line[:22]}{str(new_numbers[chain_id]).rjust(4)[:4]} {line[27:]}'
        elif line.startswith('TER'):
            new_line = f'{line[:22]}{str(new_numbers[chain_id]).rjust(4)[:4]} {line[27:]}'
        else:
            new_line = line

        renum_arr.append(new_line)

    renum_content = ''.join(renum_arr)
    return renum_content, mapped_numbers


def analyze(file_content: str) -> AnalysisOutput:

    chain_ids = parse_pdb(file_content)
    renumbered_pdb, mapped_numbers = renumber_pdb(file_content)
    mapped_values = (chain_ids, mapped_numbers)

    directory = tempfile.TemporaryDirectory()

    with tempfile.NamedTemporaryFile('w+', dir=directory.name, suffix='.pdb') as file:
        file.write(renumbered_pdb)
        file.seek(0)
        barnaba_result = barnaba.annotate(file.name)

    parsed_output = parse_barnaba(barnaba_result, mapped_values)

    base_pairs, base_stackings, other_interactions = parsed_output
    return AnalysisOutput(base_pairs, base_stackings, [], [], other_interactions)


def main() -> None:
    structure = analyze(sys.stdin.read())
    print(orjson.dumps(structure).decode('utf-8'))


if __name__ == '__main__':
    main()
