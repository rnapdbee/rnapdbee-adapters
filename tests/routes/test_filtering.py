import pytest


# Parameters: (pdb_or_cif, expected_pdb_or_cif, route)
@pytest.mark.parametrize(
    'tool_test_result',
    [
        ('2z_74.pdb', '2z_74_filter.cif', '/filtering-api/v1/filter'),
    ],
    ids=[
        '/filtering-api/v1/filter',
    ],
    indirect=True,
)
def test_filtering(tool_test_result):
    assert tool_test_result.status_code == 200
    assert tool_test_result.response == tool_test_result.expected
