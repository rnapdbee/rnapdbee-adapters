import os
from collections import namedtuple

import orjson
import pytest
from data import TEST_DIRECTORY

from adapters.server import app


@pytest.fixture()
def analysis_test_result(request):
    # Setup

    # Directory that contains input files
    INPUT_DIRECTORY = "files/input/"

    # Directory that contains output from analysis-adapter endpoint
    ANALYSIS_OUTPUT_DIRECTORY = "files/analysis_output/"

    file_path, expected_path, route = request.param

    test_directory = TEST_DIRECTORY
    file_absolute_path = os.path.abspath(
        os.path.join(
            test_directory,
            INPUT_DIRECTORY,
            file_path,
        )
    )
    expected_absolute_path = os.path.abspath(
        os.path.join(
            test_directory,
            ANALYSIS_OUTPUT_DIRECTORY,
            expected_path,
        )
    )

    app.config.update(
        {
            "TESTING": True,
        }
    )

    client = app.test_client()

    with open(file_absolute_path, encoding="utf-8") as file:
        file_content = file.read()

    with open(expected_absolute_path, encoding="utf-8") as file:
        expected = orjson.loads(file.read())

    response = client.post(
        route,
        headers={"Content-Type": "text/plain"},
        data=file_content,
    )

    Result = namedtuple("Result", "status_code response expected")
    yield Result(response.status_code, response.json, expected)
    # Teardown


# Parameters: (pdb_or_cif, expected_json, route)
@pytest.mark.parametrize(
    "analysis_test_result",
    [
        ("2z_74.pdb", "bpnet.json", "/analysis-api/v1/bpnet/1"),
        ("2z_74.pdb", "bpnet.json", "/analysis-api/v1/bpnet"),
        ("2z_74.pdb", "fr3d.json", "/analysis-api/v1/fr3d/1"),
        ("2z_74.pdb", "fr3d.json", "/analysis-api/v1/fr3d"),
        ("2z_74.pdb", "barnaba.json", "/analysis-api/v1/barnaba/1"),
        ("2z_74.pdb", "barnaba.json", "/analysis-api/v1/barnaba"),
        ("2z_74.pdb", "mc_annotate.json", "/analysis-api/v1/mc-annotate/1"),
        ("2z_74.pdb", "mc_annotate.json", "/analysis-api/v1/mc-annotate"),
        ("2z_74.pdb", "rnaview.json", "/analysis-api/v1/rnaview/1"),
        ("2z_74.pdb", "rnaview.json", "/analysis-api/v1/rnaview"),
        ("2z_74.pdb", "rnapolis.json", "/analysis-api/v1/rnapolis/1"),
        ("2z_74.pdb", "rnapolis.json", "/analysis-api/v1/rnapolis"),
    ],
    ids=[
        "/analysis-api/v1/bpnet/1",
        "/analysis-api/v1/bpnet",
        "/analysis-api/v1/fr3d/1",
        "/analysis-api/v1/fr3d",
        "/analysis-api/v1/barnaba/1",
        "/analysis-api/v1/barnaba",
        "/analysis-api/v1/mc-annotate/1",
        "/analysis-api/v1/mc-annotate",
        "/analysis-api/v1/rnaview/1",
        "/analysis-api/v1/rnaview",
        "/analysis-api/v1/rnapolis/1",
        "/analysis-api/v1/rnapolis",
    ],
    indirect=True,
)
def test_analysis(analysis_test_result):
    assert analysis_test_result.status_code == 200
    assert analysis_test_result.response == analysis_test_result.expected


@pytest.mark.parametrize(
    "analysis_test_result",
    [
        ("1ehz_mod.pdb", "icode_bpnet.json", "/analysis-api/v1/bpnet"),
        ("1ehz_mod.pdb", "icode_fr3d.json", "/analysis-api/v1/fr3d"),
        ("1ehz_mod.pdb", "icode_barnaba.json", "/analysis-api/v1/barnaba"),
        ("1ehz_mod.pdb", "icode_mc_annotate.json", "/analysis-api/v1/mc-annotate"),
        ("1ehz_mod.pdb", "icode_rnaview.json", "/analysis-api/v1/rnaview"),
        ("1ehz_mod.pdb", "icode_rnapolis.json", "/analysis-api/v1/rnapolis"),
    ],
    ids=[
        "/analysis-api/v1/bpnet",
        "/analysis-api/v1/fr3d",
        "/analysis-api/v1/barnaba",
        "/analysis-api/v1/mc-annotate",
        "/analysis-api/v1/rnaview",
        "/analysis-api/v1/rnapolis",
    ],
    indirect=True,
)
def test_icode(analysis_test_result):
    assert analysis_test_result.status_code == 200
    assert analysis_test_result.response == analysis_test_result.expected
