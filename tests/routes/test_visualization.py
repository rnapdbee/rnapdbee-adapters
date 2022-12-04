import os
from collections import namedtuple

import pytest

from adapters.server import app
from data import TEST_DIRECTORY


@pytest.fixture()
def visualization_test_result(request):
    # Setup

    # Directory that contains input files
    INPUT_DIRECTORY = 'files/input/'

    # Directory that contains output from visualization-adapter endpoint
    VISUALIZATION_OUTPUT_DIRECTORY = 'files/visualization_output/'

    file_path, expected_path, route = request.param

    test_directory = TEST_DIRECTORY
    file_absolute_path = os.path.abspath(os.path.join(
        test_directory,
        INPUT_DIRECTORY,
        file_path,
    ))
    expected_absolute_path = os.path.abspath(
        os.path.join(
            test_directory,
            VISUALIZATION_OUTPUT_DIRECTORY,
            expected_path,
        ))

    app.config.update({
        "TESTING": True,
    })

    client = app.test_client()

    with open(file_absolute_path, encoding='utf-8') as file:
        file_content = file.read()

    with open(expected_absolute_path, encoding='utf-8') as file:
        expected = file.read()

    response = client.post(
        route,
        headers={'Content-Type': 'application/json'},
        data=file_content,
    )

    Result = namedtuple('Result', 'status_code response expected')
    yield Result(response.status_code, response.data.decode('utf-8'), expected)
    # Teardown


# Parameters: (json, expected_image, route)
@pytest.mark.parametrize(
    'visualization_test_result',
    [
        ('modelMulti2D.json', 'weblogo.svg', '/visualization-api/v1/weblogo'),
        ('model2D.json', 'pseudoviewer.svg', '/visualization-api/v1/pseudoviewer'),
        ('model2D.json', 'rchie.svg', '/visualization-api/v1/rchie'),
        ('model2D.json', 'rnapuzzler.svg', '/visualization-api/v1/rnapuzzler'),
    ],
    ids=[
        '/visualization-api/v1/weblogo',
        '/visualization-api/v1/pseudoviewer',
        '/visualization-api/v1/rchie',
        '/visualization-api/v1/rnapuzzler',
    ],
    indirect=True,
)
def test_analysis(visualization_test_result):
    assert visualization_test_result.status_code == 200
    assert visualization_test_result.response == visualization_test_result.expected
