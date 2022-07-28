from adapters.model import LeontisWesthof, Residue, ResidueAuth
from adapters.barnaba_ import BarnabaAdapter
import pytest
from data import PDB_LINES, PDB_LINES_RENUMBERED, MAPPED_VALUES

# -------- FIXTURES --------


@pytest.fixture
def adapter():
    # Setup
    adapter = BarnabaAdapter()
    yield adapter
    # Teardown


@pytest.fixture
def adapter_after_pdb_parsing():
    # Setup
    adapter = BarnabaAdapter()
    adapter.chains = ['X', '-', '.', '_']
    adapter.mapped_residues_info = MAPPED_VALUES
    yield adapter
    # Teardown


@pytest.mark.parametrize(
    'file_content,expected',
    [
        (PDB_LINES[0], ['X']),
        (PDB_LINES[1], ['X']),
        (PDB_LINES[2], ['X']),
        (PDB_LINES[3], []),
    ],
)
def test_append_chains(adapter, file_content, expected):
    adapter.append_chains(file_content)
    assert adapter.chains == expected


@pytest.mark.parametrize(
    'file_content,expected_mapped_values,expected_content',
    [(
        '\n'.join(PDB_LINES[:7]),
        MAPPED_VALUES,
        '\n'.join(PDB_LINES_RENUMBERED[:7]),
    )],
)
def test_renumber_pdb(adapter, file_content, expected_mapped_values, expected_content):
    assert adapter.renumber_pdb(file_content) == expected_content
    assert adapter.mapped_residues_info == expected_mapped_values


@pytest.mark.parametrize(
    'residue_info,expected',
    [
        ('DA_1_0', Residue(None, ResidueAuth('X', '-1', 'A', 'DA'))),
        ('G_2_0', Residue(None, ResidueAuth('X', '1', 'B', 'G'))),
        ('._1_1', Residue(None, ResidueAuth('-', '-1', 'A', '.'))),
        ('-_1_2', Residue(None, ResidueAuth('.', '-1', 'A', '-'))),
        ('__1_3', Residue(None, ResidueAuth('_', '-1', None, '_'))),
    ],
)
def test_get_residue(adapter_after_pdb_parsing, residue_info, expected):
    adapter_after_pdb_parsing.get_residue(residue_info) == expected


@pytest.mark.parametrize(
    'interaction,expected',
    [
        ('XXx', None),
        ('xXx', None),
        ('xxx', None),
        ('WCc', LeontisWesthof['cWW']),
        ('GUc', LeontisWesthof['cWW']),
        ('HHt', LeontisWesthof['tHH']),
    ],
)
def test_get_leontis_westhof(adapter, interaction, expected):
    adapter.get_leontis_westhof(interaction) == expected
