#! /usr/bin/env python
import enum
import subprocess
import sys
import tempfile

import orjson

from adapters.model import BasePair, LeontisWesthof, Residue, ResidueAuth, AnalysisOutput, Stacking, StackingTopology, \
    BaseRibose, BR, BasePhosphate, BPh, OtherInteraction


class Element(enum.Enum):
    phosphate = enum.auto()
    ribose = enum.auto()
    base = enum.auto()
    unknown = enum.auto()

    @classmethod
    def assign(cls, atom_name: str):
        if atom_name in Element.phosphate.atoms():
            return Element.phosphate
        elif atom_name in Element.ribose.atoms():
            return Element.ribose
        elif atom_name in Element.base.atoms():
            return Element.base
        else:
            return Element.unknown

    def atoms(self):
        if self == Element.phosphate:
            return frozenset(("P", "OP1", "OP2", "O5'", "C5'", "C4'", "C3'", "O3'", "O5*", "C5*", "C4*", "C3*", "O3*"))
        elif self == Element.ribose:
            return frozenset(("C1'", "C2'", "O2'", "O4'", "C1*", "C2*", "O2*", "O4*"))
        elif self == Element.base:
            return frozenset(("C2", "C4", "C5", "C6", "C8", "N1", "N2", "N3", "N4", "N6", "N7", "N9", "O2", "O4", "O6"))
        else:
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
#      2       2   G ? A       14     2   G ? AB   W:HC BP 0.36    20     2   G ? AC   H:WC TP 0.36
#      3       3   G ? A       70    70   C ? A    W:WC BP 0.19
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
            resinfo = fields[1:5]
            nt1 = Residue(None, ResidueAuth(resinfo[3], int(resinfo[0]), resinfo[2], resinfo[1]))
            resinfo = fields[6:10]
            nt2 = Residue(None, ResidueAuth(resinfo[3], int(resinfo[0]), resinfo[2], resinfo[1]))
            lw = convert_lw(fields[10])
            base_pairs.append(BasePair(nt1, nt2, lw))
        elif len(fields) == 21:
            # triple
            resinfo = fields[1:5]
            nt1 = Residue(None, ResidueAuth(resinfo[3], int(resinfo[0]), resinfo[2], resinfo[1]))
            resinfo = fields[6:10]
            nt2 = Residue(None, ResidueAuth(resinfo[3], int(resinfo[0]), resinfo[2], resinfo[1]))
            lw = convert_lw(fields[10])
            base_pairs.append(BasePair(nt1, nt2, lw))
            resinfo = fields[14:18]
            nt3 = Residue(None, ResidueAuth(resinfo[3], int(resinfo[0]), resinfo[2], resinfo[1]))
            lw = convert_lw(fields[18])
            base_pairs.append(BasePair(nt1, nt3, lw))
        else:
            raise RuntimeError('Failed to parse line: ' + line)

    return base_pairs


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
                if fields[8] != 'BP':
                    chain1, chain2 = fields[6].split('-')
                    number1, number2 = map(int, fields[3].split(':'))
                    icode1, icode2 = fields[2], fields[4]
                    name1, name2 = fields[5].split(':')
                    nt1 = Residue(None, ResidueAuth(chain1, number1, icode1, name1))
                    nt2 = Residue(None, ResidueAuth(chain2, number2, icode2, name2))
                    stackings.append(Stacking(nt1, nt2, StackingTopology.unknown))
            else:
                raise RuntimeError('Failed to parse OVLP line: ' + line)
        elif line.startswith('PROX'):
            fields = line.strip().split()
            if len(fields) == 11:
                chain1, chain2 = fields[6].split('-')
                number1, number2 = map(int, fields[3].split(':'))
                icode1, icode2 = fields[2], fields[4]
                name1, name2 = fields[5].split(':')
                nt1 = Residue(None, ResidueAuth(chain1, number1, icode1, name1))
                nt2 = Residue(None, ResidueAuth(chain2, number2, icode2, name2))
                atom1, atom2 = fields[7].split(':')
                element1, element2 = Element.assign(atom1), Element.assign(atom2)

                # base-ribose
                if element1 == Element.base and element2 == Element.ribose:
                    base_ribose_interactions.append(BaseRibose(nt1, nt2, BR.unknown))
                elif element1 == Element.ribose and element2 == Element.base:
                    base_ribose_interactions.append(BaseRibose(nt2, nt1, BR.unknown))

                # base-phosphate
                if element1 == Element.base and element2 == Element.phosphate:
                    base_phosphate_interactions.append(BasePhosphate(nt1, nt2, BPh.unknown))
                elif element1 == Element.phosphate and element2 == Element.base:
                    base_phosphate_interactions.append(BasePhosphate(nt2, nt1, BPh.unknown))

                # other
                other_interactions.append(OtherInteraction(nt1, nt2))
            else:
                raise RuntimeError('Failed to parse PROX line: ' + line)

    return stackings, base_ribose_interactions, base_phosphate_interactions, other_interactions


def analyze(file_content: str) -> AnalysisOutput:
    directory = tempfile.TemporaryDirectory()
    file = tempfile.NamedTemporaryFile('w+', dir=directory.name, suffix='.cif')
    file.write(file_content)
    file.seek(0)

    subprocess.run(['bpnet.linux', file.name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    file.close()

    with open(file.name.replace('.cif', '.out')) as f:
        bpnet_output = f.read()
    with open(file.name.replace('.cif', '.rob')) as f:
        bpnet_rob = f.read()

    base_pairs = parse_base_pairs(bpnet_output)
    stackings, base_ribose_interactions, base_phosphate_interactions, other_interactions = parse_overlaps(bpnet_rob)
    return AnalysisOutput(base_pairs, stackings, base_ribose_interactions, base_phosphate_interactions, other_interactions)


def main():
    structure = analyze(sys.stdin.read())
    print(orjson.dumps(structure).decode('utf-8'))


if __name__ == '__main__':
    main()
