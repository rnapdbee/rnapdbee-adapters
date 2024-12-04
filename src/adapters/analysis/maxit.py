#! /usr/bin/env python
import logging
import sys
from tempfile import NamedTemporaryFile
from typing import Any, Dict, List, Optional, Tuple

import orjson
from rnapolis.common import (
    BaseInteractions,
    BasePair,
    LeontisWesthof,
    OtherInteraction,
    Residue,
    ResidueAuth,
    ResidueLabel,
    Saenger,
)
from rnapolis.metareader import read_metadata

from adapters.tools.maxit import ensure_mmcif

logger = logging.getLogger(__name__)


def convert_saenger(hbond_type_28: str) -> Optional[Saenger]:
    if hbond_type_28 == "?":
        return None

    try:
        index = int(hbond_type_28)
        if 1 <= index <= 28:
            return list(Saenger)[index - 1]
    except ValueError:
        pass

    return None


def convert_lw(hbond_type_12) -> Optional[LeontisWesthof]:
    if hbond_type_12 == "?":
        return None

    try:
        index = int(hbond_type_12)

        if index == 1:
            return LeontisWesthof.cWW
        if index == 2:
            return LeontisWesthof.tWW
        if index == 3:
            return LeontisWesthof.cWH
        if index == 4:
            return LeontisWesthof.tWH
        if index == 5:
            return LeontisWesthof.cWS
        if index == 6:
            return LeontisWesthof.tWS
        if index == 7:
            return LeontisWesthof.cHH
        if index == 8:
            return LeontisWesthof.tHH
        if index == 9:
            return LeontisWesthof.cHS
        if index == 10:
            return LeontisWesthof.tHS
        if index == 11:
            return LeontisWesthof.cSS
        if index == 12:
            return LeontisWesthof.tSS
    except ValueError:
        pass

    return None


def parse_base_pairs(ndb_struct_na_base_pair: List[Dict]) -> Tuple[List, List]:
    base_pairs = []
    other = []

    for entry in ndb_struct_na_base_pair:
        auth_chain_i = entry["i_auth_asym_id"]
        auth_number_i = int(entry["i_auth_seq_id"])
        auth_icode_i = (
            entry["i_PDB_ins_code"] if entry["i_PDB_ins_code"] != "?" else None
        )
        name_i = entry["i_label_comp_id"]
        auth_i = ResidueAuth(auth_chain_i, auth_number_i, auth_icode_i, name_i)

        auth_chain_j = entry["j_auth_asym_id"]
        auth_number_j = int(entry["j_auth_seq_id"])
        auth_icode_j = (
            entry["j_PDB_ins_code"] if entry["j_PDB_ins_code"] != "?" else None
        )
        name_j = entry["j_label_comp_id"]
        auth_j = ResidueAuth(auth_chain_j, auth_number_j, auth_icode_j, name_j)

        label_chain_i = entry["i_label_asym_id"]
        label_number_i = int(entry["i_label_seq_id"])
        label_i = ResidueLabel(label_chain_i, label_number_i, name_i)

        label_chain_j = entry["j_label_asym_id"]
        label_number_j = int(entry["j_label_seq_id"])
        label_j = ResidueLabel(label_chain_j, label_number_j, name_j)

        residue_i = Residue(label_i, auth_i)
        residue_j = Residue(label_j, auth_j)

        saenger = convert_saenger(entry["hbond_type_28"])
        lw = convert_lw(entry["hbond_type_12"])

        if lw is not None:
            base_pairs.append(BasePair(residue_i, residue_j, lw, saenger))
        else:
            other.append(OtherInteraction(residue_i, residue_j))

    return base_pairs, other


def analyze(file_content: str, **_: Dict[str, Any]) -> BaseInteractions:
    with NamedTemporaryFile("w+", suffix=".cif") as mmcif:
        mmcif.write(file_content)
        mmcif.seek(0)
        metadata = read_metadata(mmcif, ["ndb_struct_na_base_pair"])

    base_pairs, other_interactions = parse_base_pairs(
        metadata["ndb_struct_na_base_pair"]
    )
    return BaseInteractions(base_pairs, [], [], [], other_interactions)


def main():
    structure = analyze(sys.stdin.read())
    print(orjson.dumps(structure).decode("utf-8"))


if __name__ == "__main__":
    main()
