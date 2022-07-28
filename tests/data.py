# This file contains data (and sometimes dummy content) only for testing purposes.
# You can add data (e.g. RESIDUES[200])
# but please do not change or remove existing data (e.g. RESIDUES[0]).
# Otherwise tests will fail.

from adapters.model import Residue, ResidueAuth, Stacking, StackingTopology

RESIDUES = [
    Residue(None, ResidueAuth('X', -1, 'A', 'res')),  # 0
    Residue(None, ResidueAuth('Y', 65, 'L', '123')),  # 1
    Residue(None, ResidueAuth('X', 2, 'C', 'aBc')),  # 2
    Residue(None, ResidueAuth('Y', 64, 'K', 'G')),  # 3
    Residue(None, ResidueAuth('A', 4, None, 'U')),  # 4
    Residue(None, ResidueAuth('A', 14, None, 'T')),  # 5
    Residue(None, ResidueAuth('A', 1, 'Y', 'C')),  # 6
    Residue(None, ResidueAuth('A', 71, None, 'aaa')),  # 7
    Residue(None, ResidueAuth('A', -122, 'Y', 'u')),  # 8
    Residue(None, ResidueAuth('A', -122, None, 'B')),  # 9
    Residue(None, ResidueAuth('.', -100, None, 'C')),  # 10
    Residue(None, ResidueAuth('-', -1, None, 'K')),  # 11
    Residue(None, ResidueAuth('.', -100, 'A', 'C')),  # 12
    Residue(None, ResidueAuth('-', -1, 'a', 'U')),  # 13
    Residue(None, ResidueAuth('-', -12, 'C', 'D')),  # 14
    Residue(None, ResidueAuth('-', 0, None, 'd')),  # 15
    Residue(None, ResidueAuth('.', 111, 'Z', 'aby')),  # 16
    Residue(None, ResidueAuth('.', 2, 'X', 'I')),  # 17
]

STACKINGS = [
    Stacking(
        RESIDUES[0],
        RESIDUES[1],
        StackingTopology['upward'],
    ),
    Stacking(
        RESIDUES[12],
        RESIDUES[13],
        StackingTopology['outward'],
    ),
    Stacking(
        RESIDUES[6],
        RESIDUES[7],
        StackingTopology['inward'],
    ),
]

PDB_LINES = [
    "ATOM      1  O5'  DA X  -1A     40.280   7.360  22.271  1.00 46.51           O  ",
    "ATOM     24  C4'   G X   1B     43.568  11.968  18.795  1.00 29.54           C  ",
    "HETATM 3092  O   HOH X 403X     41.301   7.203  14.005  1.00 26.45           O  ",
    "REMARK 465       C A    17                                                      ",
    "ATOM      1  O5'   . -  -1A     40.280   7.360  22.271  1.00 46.51           O  ",
    "ATOM      1  O5'   - .  -1A     40.280   7.360  22.271  1.00 46.51           O  ",
    "ATOM      1  O5'   _ _  -1      40.280   7.360  22.271  1.00 46.51           O  "
]

PDB_LINES_RENUMBERED = [
    "ATOM      1  O5'  DA X   1      40.280   7.360  22.271  1.00 46.51           O  ",
    "ATOM     24  C4'   G X   2      43.568  11.968  18.795  1.00 29.54           C  ",
    "HETATM 3092  O   HOH X   3      41.301   7.203  14.005  1.00 26.45           O  ",
    "REMARK 465       C A    17                                                      ",
    "ATOM      1  O5'   . -   1      40.280   7.360  22.271  1.00 46.51           O  ",
    "ATOM      1  O5'   - .   1      40.280   7.360  22.271  1.00 46.51           O  ",
    "ATOM      1  O5'   _ _   1      40.280   7.360  22.271  1.00 46.51           O  "
]

MAPPED_VALUES = {
    'X': {1: (-1, 'A'), 2: (1, 'B'), 3: (403, 'X')},
    '-': {1: (-1, 'A')},
    '.': {1: (-1, 'A')},
    '_': {1: (-1, '')},
}
