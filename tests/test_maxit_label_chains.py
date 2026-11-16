import mmcif.io

from adapters.tools.maxit import normalize_label_chains

SPLIT_POLYMER = """data_test
#
loop_
_atom_site.group_PDB
_atom_site.label_asym_id
_atom_site.auth_asym_id
_atom_site.label_comp_id
_atom_site.label_seq_id
_atom_site.auth_seq_id
ATOM A A DG 1 1
ATOM B A BGM 2 2
ATOM C A DT 3 3
#
"""

CONSISTENT_POLYMER = """data_test
#
loop_
_atom_site.group_PDB
_atom_site.label_asym_id
_atom_site.auth_asym_id
_atom_site.label_comp_id
_atom_site.label_seq_id
_atom_site.auth_seq_id
ATOM A A DG 1 1
ATOM A A BGM 2 2
ATOM A A DT 3 3
HETATM W A HOH . .
#
"""

SPLIT_POLYMER_WITH_LIGAND = """data_test
#
loop_
_atom_site.group_PDB
_atom_site.label_asym_id
_atom_site.auth_asym_id
_atom_site.label_comp_id
_atom_site.label_seq_id
_atom_site.auth_seq_id
ATOM A A DG 1 1
ATOM B A BGM 2 2
ATOM C A DT 3 3
HETATM W A HOH . .
#
"""


def residues(content, tmp_path):
    path = tmp_path / "structure.cif"
    path.write_text(content)
    data = mmcif.io.IoAdapter().readFile(str(path))
    atom_site = data[0].getObj("atom_site")
    indexes = {
        name: atom_site.getAttributeIndex(name)
        for name in (
            "label_asym_id",
            "auth_asym_id",
            "label_comp_id",
            "label_seq_id",
            "auth_seq_id",
        )
    }
    return [
        tuple(str(row[indexes[name]]) for name in indexes)
        for row in atom_site.getRowList()
    ]


def test_split_polymer_label_chains_are_normalized(tmp_path):
    normalized = normalize_label_chains(SPLIT_POLYMER)
    rows = residues(normalized, tmp_path)

    assert [row[0] for row in rows] == ["A", "A", "A"]
    assert [row[3] for row in rows] == ["1", "2", "3"]
    assert [row[4] for row in rows] == ["1", "2", "3"]


def test_consistent_polymer_is_left_untouched():
    assert normalize_label_chains(CONSISTENT_POLYMER) == CONSISTENT_POLYMER


def test_ligand_label_chains_are_not_normalized(tmp_path):
    normalized = normalize_label_chains(SPLIT_POLYMER_WITH_LIGAND)
    rows = residues(normalized, tmp_path)

    assert [row[0] for row in rows] == ["A", "A", "A", "W"]
    assert rows[-1][3] == "."
