#! /usr/bin/env python
# IMPORTANT! this file cannot be named barnaba.py, because it imports from "barnaba", and Python complains about that

import re
import sys
import tempfile
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

import barnaba
import orjson
from rnapolis.common import (BasePair, LeontisWesthof, OtherInteraction,
                             Residue, ResidueAuth, Stacking, StackingTopology,
                             Structure2D)

from adapters.utils import suppress_stdout_stderr


class BarnabaAdapter:

    # Positions of resiudes info in PDB files
    CHAIN_INDEX = 21
    NUMBER_INDEX = slice(22, 26)
    ICODE_INDEX = 26

    # Tokens used in PDB files
    ATOM = 'ATOM'
    HETATM = 'HETATM'
    TER = 'TER'

    # BaRNAba uses different symbols for topology
    # so we neeed to map them
    STACKING_TOPOLOGIES = {
        '>>': 'upward',
        '<<': 'downward',
        '<>': 'outward',
        '><': 'inward',
    }

    RESIDUE_REGEX = re.compile(r'(.+)_([0-9]+)_([0-9]+)')

    def __init__(self) -> None:
        # In the case of BaRNAba BasePhosphateIneractions
        # and BaseRiboseInteractions are always empty
        self.analysis_output = Structure2D([], [], [], [], [])
        # BaRNAba replaces chain identifiers with numbers
        # so we need to remember them before processing
        self.chains: List[str] = []
        # Since BaRNAba does not use insertion code
        # we need to renumber sequence numbers in PDB
        # and remember old values - number and icode
        # usage: new_numbers[chain][new_number] = (old_number, icode)
        self.mapped_residues_info: Dict[str, Dict[int, Tuple[int, str]]] = defaultdict(dict)

    def get_residue(self, residue_info: str) -> Residue:
        residue_info_list = re.search(self.RESIDUE_REGEX, residue_info).groups()
        # Expects [name, number, chain_index]
        assert len(residue_info_list) == 3
        chain = self.chains[int(residue_info_list[2])]
        name = residue_info_list[0]
        new_number = int(residue_info_list[1])
        number, icode = self.mapped_residues_info[chain][new_number]
        icode = None if icode == '' else icode
        return Residue(None, ResidueAuth(chain, number, icode, name))

    def get_leontis_westhof(self, interaction: str) -> Optional[LeontisWesthof]:
        # Unknown interaction for BaRNAba
        # so classify it as OtherIneraction
        if 'x' in interaction.lower():
            return None

        # BaRNAba uses these aliases for cWW in our model
        if interaction in ('WCc', 'GUc'):
            return LeontisWesthof.cWW

        return LeontisWesthof[f'{interaction[2]}{interaction[:2]}']

    def append_chains(self, file_content: str) -> None:
        for line in file_content.splitlines():
            if line.startswith(self.ATOM) or line.startswith(self.HETATM):
                if line[self.CHAIN_INDEX] not in self.chains:
                    self.chains.append(line[self.CHAIN_INDEX])

    def append_interactions(self, pairings: List[str], residues: List[str]) -> None:
        for p, pairing in enumerate(pairings[0][0]):
            residue_info_left, residue_info_right = residues[pairing[0]], residues[pairing[1]]
            interaction = pairings[0][1][p]
            nt1 = self.get_residue(residue_info_left)
            nt2 = self.get_residue(residue_info_right)
            lw = self.get_leontis_westhof(interaction)
            if lw is None:
                self.analysis_output.otherInteractions.append(OtherInteraction(nt1, nt2))
            else:
                self.analysis_output.basePairs.append(BasePair(nt1, nt2, lw, None))

    def append_stackings(self, stackings: List[str], residues: List[str]) -> None:
        for s, stacking in enumerate(stackings[0][0]):
            residue_info_left, residue_info_right = residues[stacking[0]], residues[stacking[1]]
            interaction = stackings[0][1][s]
            nt1 = self.get_residue(residue_info_left)
            nt2 = self.get_residue(residue_info_right)
            topology = StackingTopology[self.STACKING_TOPOLOGIES[interaction]]
            self.analysis_output.stackings.append(Stacking(nt1, nt2, topology))

    # This function renumbers pdb and removes icode from file
    def renumber_pdb(self, file_content: str) -> str:
        # Counter for each chain
        # usage: new_numbers[chain] = new_number
        new_numbers = defaultdict(int)
        # For efficiency save content in list and use join()
        renumbered_content_list = []

        for line in file_content.splitlines(True):
            if line.startswith(self.ATOM) or line.startswith(self.HETATM):
                old_number = int(line[self.NUMBER_INDEX].strip())
                icode = line[self.ICODE_INDEX].strip()
                chain = line[self.CHAIN_INDEX].strip()
                if (old_number, icode) not in self.mapped_residues_info[chain].values():
                    new_numbers[chain] += 1
                    self.mapped_residues_info[chain][new_numbers[chain]] = (old_number, icode)
                new_line = f'{line[:22]}{str(new_numbers[chain]).rjust(4)[:4]} {line[27:]}'
            elif line.startswith(self.TER):
                new_line = f'{line[:22]}{str(new_numbers[chain]).rjust(4)[:4]} {line[27:]}'
            else:
                new_line = line

            renumbered_content_list.append(new_line)

        renumbered_content = ''.join(renumbered_content_list)
        return renumbered_content

    @classmethod
    def run_barnaba(cls, file_content: str) -> str:
        with tempfile.TemporaryDirectory() as directory_name:
            with tempfile.NamedTemporaryFile('w+', dir=directory_name, suffix='.pdb') as file:
                file.write(file_content)
                file.seek(0)
                with suppress_stdout_stderr():
                    try:
                        barnaba_result = barnaba.annotate(file.name)
                    except SystemExit as exception:
                        raise RuntimeError('BaRNAba failed') from exception
        return barnaba_result

    def analyze(self, file_content: str) -> Structure2D:
        self.append_chains(file_content)
        renumbered_pdb: str = self.renumber_pdb(file_content)
        stackings, pairings, res = self.run_barnaba(renumbered_pdb)

        self.append_interactions(pairings, res)
        self.append_stackings(stackings, res)
        return self.analysis_output


def main() -> None:
    barnaba_adapter = BarnabaAdapter()
    structure = barnaba_adapter.analyze(sys.stdin.read())
    print(orjson.dumps(structure).decode('utf-8'))


if __name__ == '__main__':
    main()
