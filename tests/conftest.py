import os
from collections import namedtuple

import pytest

from adapters.server import app
from data import TEST_DIRECTORY


@pytest.fixture()
def tool_test_result(request):
    # Setup

    # Directory that contains input files
    INPUT_DIRECTORY = 'files/input/'

    # Directory that contains output from tools endpoints (conversion or filtering)
    TOOL_OUTPUT_DIRECTORY = 'files/tools_output/'

    file_path, expected_path, route = request.param

    file_absolute_path = os.path.abspath(os.path.join(
        TEST_DIRECTORY,
        INPUT_DIRECTORY,
        file_path,
    ))
    expected_absolute_path = os.path.abspath(os.path.join(
        TEST_DIRECTORY,
        TOOL_OUTPUT_DIRECTORY,
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
        headers={'Content-Type': 'text/plain'},
        data=file_content,
    )

    Result = namedtuple('Result', 'status_code response expected')
    yield Result(response.status_code, response.data.decode('utf-8'), expected)
    # Teardown
