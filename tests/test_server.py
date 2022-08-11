from collections import namedtuple
import pytest
from adapters.server import app
import os
import json

# -------- FIXTURES AND HELPERS --------

# Directory that contains input files (only text files, e.g. pdb, cif)
INPUT_DIRECTORY = 'files/input/'

# Directory that contains output from adapter endpoint (only json files)
ADAPTER_OUTPUT_DIRECTORY = 'files/adapter_output/'

# Directory that contains output from any other endpoint (only text files, e.g. pdb, cif)
TOOL_OUTPUT_DIRECTORY = 'files/tool_output/'


@pytest.fixture()
def adapter_test_result(request):
    # Setup
    file_path, expected_path, route = request.param

    test_directory = os.path.dirname(os.path.abspath(__file__))
    file_absolute_path = os.path.abspath(os.path.join(
        test_directory,
        INPUT_DIRECTORY,
        file_path,
    ))
    expected_absolute_path = os.path.abspath(os.path.join(
        test_directory,
        ADAPTER_OUTPUT_DIRECTORY,
        expected_path,
    ))

    app.config.update({
        "TESTING": True,
    })

    client = app.test_client()

    with open(file_absolute_path) as file:
        file_content = file.read()

    with open(expected_absolute_path) as file:
        expected = json.load(file)

    response = client.post(
        route,
        headers={'Content-Type': 'text/plain'},
        data=file_content,
    )

    Result = namedtuple('Result', 'status_code response expected')
    yield Result(response.status_code, response.json, expected)
    # Teardown


@pytest.fixture()
def tool_test_result(request):
    # Setup
    file_path, expected_path, route = request.param

    test_directory = os.path.dirname(os.path.abspath(__file__))
    file_absolute_path = os.path.abspath(os.path.join(
        test_directory,
        INPUT_DIRECTORY,
        file_path,
    ))
    expected_absolute_path = os.path.abspath(os.path.join(
        test_directory,
        TOOL_OUTPUT_DIRECTORY,
        expected_path,
    ))

    app.config.update({
        "TESTING": True,
    })

    client = app.test_client()

    with open(file_absolute_path) as file:
        file_content = file.read()

    with open(expected_absolute_path) as file:
        expected = file.read()

    response = client.post(
        route,
        headers={'Content-Type': 'text/plain'},
        data=file_content,
    )

    Result = namedtuple('Result', 'status_code response expected')
    yield Result(response.status_code, response.data.decode('utf-8'), expected)
    # Teardown


# -------- TESTS --------


# Parameters: (pdb_or_cif, expected_json, route)
@pytest.mark.parametrize(
    'adapter_test_result',
    [
        ('2z_74.pdb', 'bpnet.json', '/analyze/bpnet/1'),
        ('2z_74.pdb', 'bpnet.json', '/analyze/bpnet'),
        ('2z_74.pdb', 'bpnet.json', '/analyze/1'),
        ('2z_74.pdb', 'bpnet.json', '/analyze'),
        ('2z_74.pdb', 'fr3d.json', '/analyze/fr3d/1'),
        ('2z_74.pdb', 'fr3d.json', '/analyze/fr3d'),
        ('2z_74.pdb', 'barnaba.json', '/analyze/barnaba/1'),
        ('2z_74.pdb', 'barnaba.json', '/analyze/barnaba'),
        ('2z_74.pdb', 'mc_annotate.json', '/analyze/mc-annotate/1'),
        ('2z_74.pdb', 'mc_annotate.json', '/analyze/mc-annotate'),
    ],
    ids=[
        '/analyze/bpnet/1',
        '/analyze/bpnet',
        '/analyze/1',
        '/analyze',
        '/analyze/fr3d/1',
        '/analyze/fr3d',
        '/analyze/barnaba/1',
        '/analyze/barnaba',
        '/analyze/mc-annotate/1',
        '/analyze/mc-annotate',
    ],
    indirect=True,
)
def test_adapter(adapter_test_result):
    assert adapter_test_result.status_code == 200
    assert adapter_test_result.response == adapter_test_result.expected


@pytest.mark.parametrize(
    'adapter_test_result',
    [
        ('1ehz_mod.pdb', 'icode_bpnet.json', '/analyze/bpnet'),
        ('1ehz_mod.pdb', 'icode_fr3d.json', '/analyze/fr3d'),
        ('1ehz_mod.pdb', 'icode_barnaba.json', '/analyze/barnaba'),
        ('1ehz_mod.pdb', 'icode_mc_annotate.json', '/analyze/mc-annotate'),
    ],
    ids=[
        '/analyze/bpnet',
        '/analyze/fr3d',
        '/analyze/barnaba',
        '/analyze/mc-annotate',
    ],
    indirect=True,
)
def test_icode(adapter_test_result):
    assert adapter_test_result.status_code == 200
    assert adapter_test_result.response == adapter_test_result.expected


# Parameters: (pdb_or_cif, expected_pdb_or_cif, route)
@pytest.mark.parametrize(
    'tool_test_result',
    [
        ('2z_74.pdb', '2z_74.cif', '/convert/ensure-cif'),
        ('2z_74.cif', '2z_74_out.pdb', '/convert/ensure-pdb'),
        ('2z_74.pdb', '2z_74_filter.cif', '/filter'),
    ],
    ids=[
        '/convert/ensure-cif',
        '/convert/ensure-pdb',
        '/filter',
    ],
    indirect=True,
)
def test_tool(tool_test_result):
    assert tool_test_result.status_code == 200
    assert tool_test_result.response == tool_test_result.expected
