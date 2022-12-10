#! /usr/bin/env python
import enum
import os.path
import sys
from tempfile import NamedTemporaryFile, TemporaryDirectory

import orjson
from rnapolis.common import (BasePair, BasePhosphate, BaseRibose, LeontisWesthof, OtherInteraction, Residue,
                             ResidueAuth, Stacking, Structure2D)

from adapters.tools.utils import run_external_cmd


class Element(enum.Enum):
    PHOSPHATE = enum.auto()
    RIBOSE = enum.auto()
    BASE = enum.auto()
    UNKNOWN = enum.auto()

    @classmethod
    def assign(cls, atom_name: str):
        if atom_name in Element.PHOSPHATE.atoms():
            return Element.PHOSPHATE
        if atom_name in Element.RIBOSE.atoms():
            return Element.RIBOSE
        if atom_name in Element.BASE.atoms():
            return Element.BASE
        return Element.UNKNOWN

    def atoms(self):
        if self == Element.PHOSPHATE:
            return frozenset(("P", "OP1", "OP2", "O5'", "C5'", "C4'", "C3'", "O3'", "O5*", "C5*", "C4*", "C3*", "O3*"))
        if self == Element.RIBOSE:
            return frozenset(("C1'", "C2'", "O2'", "O4'", "C1*", "C2*", "O2*", "O4*"))
        if self == Element.BASE:
            return frozenset(("C2", "C4", "C5", "C6", "C8", "N1", "N2", "N3", "N4", "N6", "N7", "N9", "O2", "O4", "O6"))
        raise NotImplementedError()


# BASE PAIR EDGE
#
# 	W - Watson-Crick edge (Capital W).
# 	H - Hoogsteen edge (Capital H).
# 	S - Sugar edge (Capital S).
# 		w - Watson-Crick edge with one or more C-H...O/N type of hydrogen bond (Small w).
# 		h - Hoogsteen edge with one or more C-H...O/N type of hydrogen bond (Small h).
# 		s - Sugar edge with one or more C-H...O/N type of hydrogen bond (Small s).
# 		+ - Protonated Watson-Crick edge.
# 		z - Protonated Sugar edge.
# 		g - Protonated Hoogsteen edge (rarely found though).
def convert_lw(bpnet_lw) -> LeontisWesthof:
    assert len(bpnet_lw) == 4
    bpnet_lw = bpnet_lw.replace('+', 'W').replace('z', 'S').replace('g', 'H')
    edge5 = bpnet_lw[0].upper()
    edge3 = bpnet_lw[2].upper()
    stericity = bpnet_lw[3].lower()
    return LeontisWesthof[f'{stericity}{edge5}{edge3}']


# Example lines:
#      1       1   U ? A
#      3       3   G ? A       70    70   C ? A    W:WC BP 0.19
#      2       2   G ? A       14     2   G ? AB   W:HC BP 0.36    20     2   G ? AC   H:WC TP 0.36
#      1       1   G ? A        3     3   A ? A    S:HT BP 0.62    13    13   G ? A    H:WC TP 0.80...
#      4     4   G ? A    W:HC TP 1.31
def parse_base_pairs(bpnet_output: str):
    base_pairs = []

    for line in bpnet_output.splitlines():
        if line.startswith('#'):
            continue

        fields = line.strip().split()

        if len(fields) == 5:
            # unpaired residue
            pass
        elif len(fields) == 13:
            # pair
            nt1 = residue_from_pair(fields[1:5])
            nt2 = residue_from_pair(fields[6:10])
            lw = convert_lw(fields[10])
            base_pairs.append(BasePair(nt1, nt2, lw, None))
        elif len(fields) == 21:
            # triple
            nt1 = residue_from_pair(fields[1:5])
            nt2 = residue_from_pair(fields[6:10])
            lw = convert_lw(fields[10])
            base_pairs.append(BasePair(nt1, nt2, lw, None))
            nt3 = residue_from_pair(fields[14:18])
            lw = convert_lw(fields[18])
            base_pairs.append(BasePair(nt1, nt3, lw, None))
        elif len(fields) == 29:
            # quadruple
            nt1 = residue_from_pair(fields[1:5])
            nt2 = residue_from_pair(fields[6:10])
            lw = convert_lw(fields[10])
            base_pairs.append(BasePair(nt1, nt2, lw, None))
            nt3 = residue_from_pair(fields[14:18])
            lw = convert_lw(fields[18])
            base_pairs.append(BasePair(nt1, nt3, lw, None))
            nt4 = residue_from_pair(fields[22:26])
            lw = convert_lw(fields[26])
            base_pairs.append(BasePair(nt1, nt4, lw, None))
        else:
            raise RuntimeError('Failed to parse line: ' + line)

    return base_pairs


# Examples:
# 2   G ? A
#         ^--- chain name
#       ^----- insertion code
#     ^------- residue name
# ^----------- residue number
def residue_from_pair(resinfo):
    icode = None if resinfo[2] in ' ?' else resinfo[2]
    auth = ResidueAuth(resinfo[3], int(resinfo[0]), icode, resinfo[1])
    return Residue(None, auth)


# Example lines:
# OVLP         2:3       ?      2:3      ?     G:G       A-A    ASTK  --  :    30.15    187.10   186.90
# OVLP         2:14      ?      2:2      ?     G:G       A-AB   W:HC  BP  :    16.85    187.10   188.10
# PROX         2:14      ?      2:2      ?     G:G       A-AB    N2:N7   PX  :    2.83
def parse_overlaps(bpnet_output: str):
    stackings = []
    base_ribose_interactions = []
    base_phosphate_interactions = []
    other_interactions = []

    for line in bpnet_output.splitlines():
        if line.startswith('OVLP'):
            fields = line.strip().split()
            if len(fields) == 13:
                # ABVR      ASTK means Adjacent Stacking.
                # ABVR      OSTK means Non-Adjacent Stacking.
                # ABVR      ADJA means Adjacent contact but not proper stacking.
                # ABVR      CROS means Cross overlap between BP and the opposite Diagonal.
                # ABVR      CLOS means Otherwise overlap between any two bases.
                if fields[7] in ['ASTK', 'OSTK', 'ADJA']:
                    # TODO: below you can infer StackingTopology from the fields
                    nt1, nt2 = residues_from_overlap_info(fields)
                    stackings.append(Stacking(nt1, nt2, None))
            else:
                raise RuntimeError('Failed to parse OVLP line: ' + line)
        elif line.startswith('PROX'):
            fields = line.strip().split()
            if len(fields) == 11:
                nt1, nt2 = residues_from_overlap_info(fields)
                atom1, atom2 = fields[7].split(':')
                element1, element2 = Element.assign(atom1), Element.assign(atom2)

                # TODO: below you can infer the BR classification from atom names
                # base-ribose
                if element1 == Element.BASE and element2 == Element.RIBOSE:
                    base_ribose_interactions.append(BaseRibose(nt1, nt2, None))
                elif element1 == Element.RIBOSE and element2 == Element.BASE:
                    base_ribose_interactions.append(BaseRibose(nt2, nt1, None))

                # TODO: below you can infer the BPh classification from atom names
                # base-phosphate
                if element1 == Element.BASE and element2 == Element.PHOSPHATE:
                    base_phosphate_interactions.append(BasePhosphate(nt1, nt2, None))
                elif element1 == Element.PHOSPHATE and element2 == Element.BASE:
                    base_phosphate_interactions.append(BasePhosphate(nt2, nt1, None))

                # other
                other_interactions.append(OtherInteraction(nt1, nt2))
            else:
                raise RuntimeError('Failed to parse PROX line: ' + line)

    return stackings, base_ribose_interactions, base_phosphate_interactions, other_interactions


# Example:
# OVLP         2:3       ?      2:3      ?     G:G       A-A
#                                                         ^--- chains
#                                               ^------------- residue names
#                                        ^-------------------- insertion code (rhs)
#                                ^---------------------------- residue numbers
#                        ^------------------------------------ insertion code (lhs)
def residues_from_overlap_info(fields):
    chain1, chain2 = fields[6].split('-')
    number1, number2 = map(int, fields[3].split(':'))
    icode1, icode2 = fields[2], fields[4]
    name1, name2 = fields[5].split(':')

    if icode1 in ' ?':
        icode1 = None
    if icode2 in ' ?':
        icode2 = None

    nt1 = Residue(None, ResidueAuth(chain1, number1, icode1, name1))
    nt2 = Residue(None, ResidueAuth(chain2, number2, icode2, name2))
    return nt1, nt2


def analyze(cif_content: str) -> Structure2D:
    with TemporaryDirectory() as directory:
        with NamedTemporaryFile('w+', dir=directory, suffix='.cif') as file:
            file.write(cif_content)
            file.seek(0)
            run_external_cmd(['bpnet.linux', file.name], cwd=directory)

            if os.path.exists(file.name.replace('.cif', '.out')):
                with open(file.name.replace('.cif', '.out'), encoding='utf-8') as bpnet_file:
                    bpnet_output = bpnet_file.read()
                base_pairs = parse_base_pairs(bpnet_output)
            else:
                base_pairs = []

            if os.path.exists(file.name.replace('.cif', '.rob')):
                with open(file.name.replace('.cif', '.rob'), encoding='utf-8') as bpnet_file:
                    bpnet_rob = bpnet_file.read()
                stackings, base_ribose_interactions, base_phosphate_interactions, other_interactions = parse_overlaps(
                    bpnet_rob)
            else:
                stackings, base_ribose_interactions, base_phosphate_interactions, other_interactions = [], [], [], []

    return Structure2D(base_pairs, stackings, base_ribose_interactions, base_phosphate_interactions, other_interactions)


def main():
    structure = analyze(sys.stdin.read())
    print(orjson.dumps(structure).decode('utf-8'))


if __name__ == '__main__':
    main()
