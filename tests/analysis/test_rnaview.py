import gzip

import orjson

from adapters.analysis import rnaview
from adapters.services import run_pdb_adapter


def test_4gqj():
    with open("files/input/4gqj-assembly1.cif") as f:
        file_content = f.read()

    actual_base_interactions = run_pdb_adapter(rnaview.analyze, file_content, 1)
    actual_base_interactions = orjson.loads(orjson.dumps(actual_base_interactions))

    with open("files/analysis_output/4gqj-assembly1-rnaview.json") as f:
        expected_base_interactions = orjson.loads(f.read())

    assert actual_base_interactions == expected_base_interactions


def test_279d():
    with gzip.open("files/input/279d-assembly1.cif.gz", "rt") as f:
        file_content = f.read()

    actual_base_interactions = run_pdb_adapter(rnaview.analyze, file_content, 1)
    actual_base_interactions = orjson.loads(orjson.dumps(actual_base_interactions))

    with open("files/analysis_output/279d-assembly1-rnaview.json") as f:
        expected_base_interactions = orjson.loads(f.read())

    assert actual_base_interactions == expected_base_interactions


def test_R1107TS091_1():
    with open("files/input/R1107TS091_1.pdb") as f:
        file_content = f.read()

    adapter = rnaview.RNAViewAdapter()
    adapter.analyze_by_rnaview(file_content)
    assert len(adapter.residues_from_pdb) == 69
