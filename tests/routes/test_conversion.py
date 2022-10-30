import pytest


# Parameters: (pdb_or_cif, expected_pdb_or_cif, route)
@pytest.mark.parametrize(
    'tool_test_result',
    [
        ('2z_74.pdb', '2z_74.cif', '/conversion-api/v1/ensure-cif'),
        ('2z_74.cif', '2z_74_out.pdb', '/conversion-api/v1/ensure-pdb'),
    ],
    ids=[
        '/conversion-api/v1/ensure-cif',
        '/conversion-api/v1/ensure-pdb',
    ],
    indirect=True,
)
def test_tool(tool_test_result):
    assert tool_test_result.status_code == 200
    assert tool_test_result.response == tool_test_result.expected
