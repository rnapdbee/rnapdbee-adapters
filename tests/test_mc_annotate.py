from contextlib import \
    ExitStack as does_not_raise  # ExitStack for support Python 3.3+

import pytest
from data import PDB_LINES, RESIDUES, STACKINGS
from rnapolis.common import (BasePair, BasePhosphate, BaseRibose,
                             LeontisWesthof, Saenger)

from adapters.mc_annotate import MCAnnotateAdapter

# -------- FIXTURES --------


@pytest.fixture
def adapter():
    # Setup
    adapter = MCAnnotateAdapter()
    yield adapter
    # Teardown


@pytest.fixture
def adapter_with_names():
    # Setup
    adapter = MCAnnotateAdapter()
    names = {}
    for res in RESIDUES:
        if res.auth.icode is None:
            key = f'{res.auth.chain}{res.auth.number}'
        else:
            key = f'{res.auth.chain}{res.auth.number}.{res.auth.icode}'
        names[key] = res.auth.name

    adapter.names = names
    yield adapter
    # Teardown


# -------- TESTS --------


@pytest.mark.parametrize(
    'type,edge',
    [
        ('C8', 'H'),
        ('Ww', 'W'),
        ('Sw', 'S'),
    ],
)
def test_classify_edge(adapter, type, edge):
    assert adapter.classify_edge(type) == edge


@pytest.mark.parametrize(
    'type,expected',
    [
        ('ww', pytest.raises(ValueError)),
        ('Ww/Ww', pytest.raises(ValueError)),
        ('Bh', does_not_raise()),
    ],
)
def test_classify_edge_exception(adapter, type, expected):
    with expected:
        adapter.classify_edge(type)


@pytest.mark.parametrize(
    'residues_info,expected',
    [
        ('X-1.A-Y65.L', (RESIDUES[0], RESIDUES[1])),
        ('X2.C-Y64.K', (RESIDUES[2], RESIDUES[3])),
        ('A4-A14', (RESIDUES[4], RESIDUES[5])),
        ('A1.Y-A71', (RESIDUES[6], RESIDUES[7])),
        ('A-122.Y-A-122', (RESIDUES[8], RESIDUES[9])),
        ('.-100---1', (RESIDUES[10], RESIDUES[11])),
        ('.-100.A---1.a', (RESIDUES[12], RESIDUES[13])),
        ('--12.C--0', (RESIDUES[14], RESIDUES[15])),
        ('.111.Z-.2.X', (RESIDUES[16], RESIDUES[17])),
        ("'9'2.X-'''2.X", (RESIDUES[18], RESIDUES[19])),
    ],
)
def test_get_residues(adapter_with_names, residues_info, expected):
    assert adapter_with_names.get_residues(residues_info) == expected


@pytest.mark.parametrize(
    'line,topology_position,expected',
    [
        ('X-1.A-Y65.L : adjacent_5p upward', 3, [STACKINGS[0]]),
        ('.-100.A---1.a : outward', 2, [STACKINGS[1]]),
        ('A1.Y-A71 : inward pairing', 2, [STACKINGS[2]]),
        ("'9'2.X-'''2.X : inward pairing", 2, [STACKINGS[3]]),
    ],
)
def test_append_stacking(adapter_with_names, line, topology_position, expected):
    adapter_with_names.append_stacking(line, topology_position)
    assert adapter_with_names.analysis_output.stackings == expected


@pytest.mark.parametrize(
    'residues,token,expected',
    [
        ((RESIDUES[0], RESIDUES[1]), "O2'/Hh", BaseRibose(RESIDUES[1], RESIDUES[0], None)),
        ((RESIDUES[0], RESIDUES[1]), "Hh/O2'", BaseRibose(RESIDUES[0], RESIDUES[1], None)),
        ((RESIDUES[6], RESIDUES[12]), "O2'/SS", BaseRibose(RESIDUES[12], RESIDUES[6], None)),
    ],
)
def test_get_ribose_interaction(adapter_with_names, residues, token, expected):
    assert adapter_with_names.get_ribose_interaction(residues, token) == expected


@pytest.mark.parametrize(
    'residues,token,expected',
    [
        ((RESIDUES[0], RESIDUES[1]), "O2P/Hh", BasePhosphate(RESIDUES[1], RESIDUES[0], None)),
        ((RESIDUES[0], RESIDUES[1]), "Hh/O2P", BasePhosphate(RESIDUES[0], RESIDUES[1], None)),
        ((RESIDUES[6], RESIDUES[12]), "O2P/SS", BasePhosphate(RESIDUES[12], RESIDUES[6], None)),
    ],
)
def test_get_phosphate_interaction(adapter_with_names, residues, token, expected):
    assert adapter_with_names.get_phosphate_interaction(residues, token) == expected


@pytest.mark.parametrize(
    'residues,token,tokens,expected',
    [
        (
            (RESIDUES[0], RESIDUES[1]),
            "Ss/Ss",
            ['Ss/Ss', "O2'/Ww", 'pairing', 'parallel', 'trans', '57'],
            BasePair(RESIDUES[0], RESIDUES[1], LeontisWesthof['tSS'], None),
        ),
        (
            (RESIDUES[4], RESIDUES[5]),
            "Hw/Sw",
            ['Hw/Sw', 'pairing', 'antiparallel', 'trans', 'one_hbond', '112'],
            BasePair(RESIDUES[4], RESIDUES[5], LeontisWesthof['tHS'], None),
        ),
        (
            (RESIDUES[6], RESIDUES[12]),
            "Ww/Ww",
            ['Ww/Ww', 'pairing', 'antiparallel', 'cis', 'XIX'],
            BasePair(RESIDUES[6], RESIDUES[12], LeontisWesthof['cWW'], Saenger['XIX']),
        ),
    ],
)
def test_get_base_interaction(adapter_with_names, residues, token, tokens, expected):
    assert adapter_with_names.get_base_interaction(residues, token, tokens) == expected


@pytest.mark.parametrize(
    'file_content,expected',
    [
        (PDB_LINES[0], {'X-1.A': 'DA'}),
        (PDB_LINES[1], {'X1.B', 'G'}),
        (PDB_LINES[2], {'X403.X': 'HOH'}),
        (PDB_LINES[3], {}),
        (PDB_LINES[4], {'--1.A': '.'}),
        (PDB_LINES[5], {'.-1.A': '-'}),
        (PDB_LINES[6], {'_-1.A:': '_'}),
    ],
    ids=[
        'LINE 0',
        'LINE 1',
        'LINE 2',
        'LINE 3',
        'LINE 4',
        'LINE 5',
        'LINE 6',
    ],
)
def test_append_names(adapter, file_content, expected):
    adapter.append_names(file_content)
    adapter.names == expected
