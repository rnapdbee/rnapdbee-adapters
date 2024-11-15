from src.adapters.analysis.bpnet import analyze


def test_analyze_200d_assembly1():
    """Test if BPNET analysis of 200d-assembly1.cif raises appropriate exception"""
    with open("tests/files/input/200d-assembly1.cif") as f:
        content = f.read()

    analyze(content)
