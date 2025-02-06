#! /usr/bin/env python
import logging
import math
import re
import sys
import tempfile
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import orjson
from rnapolis.common import (
    BaseInteractions,
    BasePair,
    BasePhosphate,
    BaseRibose,
    LeontisWesthof,
    OtherInteraction,
    Residue,
    ResidueAuth,
    Saenger,
    Stacking,
)

from adapters.exceptions import PdbParsingError, RegexError
from adapters.tools.utils import run_external_cmd

logger = logging.getLogger(__name__)


class RNAViewAdapter:
    RNAVIEW_REGEX = re.compile(
        "\\s*(\\d+)_(\\d+),\\s+(\\w):\\s+(-?\\d+)\\s+(\\w+)-(\\w+)\\s+"
        + "(-?\\d+)\\s+(\\w):\\s+(syn|\\s+)*((./.)\\s+(cis|tran)"
        + "(syn|\\s+)*([IVX,]+|n/a|![^.]+)|stacked)\\.?"
    )

    #    * Example lines:
    #    *      1_72, A:     1 G-C    72 A: +/+ cis         XIX
    #    *      4_69, A:     4 G-U    69 A: W/W cis         XXVIII
    #    *      5_68, A:     5 A-U    68 A: -/- cis         XX
    #    *      9_23, A:     9 A-A    23 A: H/H tran   syn    II
    #    *     16_59, A:    16 u-U    59 A: S/W tran   syn    n/a
    #    *     30_31, A:    30 G-A    31 A:      stacked
    #    *     10_45, A:    10 g-G    45 A: H/S cis         !1H(b_b)
    #    *      9_11, A:     9 A-C    11 A: S/H cis    syn    !(b_s)
    #    *     49_50, A:    50 A-G    51 A: S/. tran        !(s_s)
    #    *     48_57, A:    49 A-G    58 A: ?/W tran        !(s_s)
    #    *     1_185, A:    -2 G-A   184 A: W/W cis         VIII
    #    *   137_223, A:   138 A-A   224 A: W/S cis    syn syn  n/a
    #    * 1750_2416, 0:  1838 U-U  2621 0: W/W tran        XII,XIII
    #    * 1269_1270, 0:  1356 A-A  1357 0: syn syn  stacked
    #    * 1500_1501, 0:  1588 G-G  1589 0:   syn  stacked
    #    *     15_22, A:    15 G-A    22 A: W/S cis         !1H(b_b).
    #    *     26_46, A:    26 C-U    46 A: W/W cis         !1H(b_b)
    #    *      8_47, A:     8 U-G    47 A: S/W cis         !(b_s)
    #    *       7_8, A:     7 G-U     8 A: S/S cis         !(s_s)

    #    * Group 1: first residue, rnaview internal index
    #    * Group 2: second residue, rnaview internal index
    #    * Group 3: first residue, chain
    #    * Group 4: first residue, number
    #    * Group 5: first residue, name
    #    * Group 6: second residue, name
    #    * Group 7: second residue, number
    #    * Group 8: second residue, chain
    #    * Group 9: ignore
    #    * Group 10: word "stacked" or bp classification
    #    * Group 11: if bp classification, then Leontis Westhof edge codes
    #    * Group 12: if bp classification, then Leontis Westhof "cis" or "tran" word
    #    * Group 13: ignore
    #    * Group 14: if bp classification, then Saenger classification OR one of:
    #    * !1H(b_b), !(b_s), !(s_s) or !b_(O1P,O2P)

    @dataclass
    class PotentialResidue:
        residue: Residue
        position_c2: Optional[Tuple[float, float, float]]
        position_c6: Optional[Tuple[float, float, float]]
        position_n1: Optional[Tuple[float, float, float]]
        position_n9: Optional[Tuple[float, float, float]]

        def is_correct_according_to_rnaview(self) -> bool:
            if any(
                (
                    self.position_c2 is None,
                    self.position_c6 is None,
                    self.position_n1 is None,
                )
            ):
                return False
            distance_c2_c6 = math.dist(self.position_c2, self.position_c6)  # type: ignore
            distance_n1_c6 = math.dist(self.position_n1, self.position_c6)  # type: ignore
            distance_n1_c2 = math.dist(self.position_n1, self.position_c2)  # type: ignore
            if all(
                (distance_c2_c6 <= 3.0, distance_n1_c6 <= 2.0, distance_n1_c2 <= 2.0)
            ):
                if self.position_n9 is not None:
                    distance_n1_n9 = math.dist(self.position_n1, self.position_n9)  # type: ignore
                    return 3.5 <= distance_n1_n9 <= 4.5
                return True
            return False

    # Positions of resiudes info in PDB files
    ATOM_NAME_INDEX = slice(12, 16)
    CHAIN_INDEX = 21
    NUMBER_INDEX = slice(22, 26)
    ICODE_INDEX = 26
    NAME_INDEX = slice(17, 20)
    X_INDEX, Y_INDEX, Z_INDEX = slice(30, 38), slice(38, 46), slice(46, 54)

    # Tokens used in PDB files
    ATOM = "ATOM"
    HETATM = "HETATM"
    ATOM_C6 = "C6"
    ATOM_C2 = "C2"
    ATOM_N1 = "N1"
    ATOM_N9 = "N9"

    # Groups of RNAVIEW_REGEX

    # RNAView tokens
    BEGIN_BASE_PAIR = "BEGIN_base-pair"
    END_BASE_PAIR = "END_base-pair"
    STACKING = "stacked"
    BASE_RIBOSE = "!(b_s)"
    BASE_PHOSPHATE = "!b_(O1P,O2P)"
    OTHER_INTERACTION = "!(s_s)"
    SAENGER_UNKNOWN = "n/a"
    PLUS_INTERACTION = "+/+"  # For us - cWW
    MINUS_INTERACTION = "-/-"  # For us - cWW
    X_INTERACTION = "X/X"  # For us - cWW
    ONE_HBOND = "!1H(b_b)"  # For us - OtherInteraction
    DOUBLE_SAENGER = ("XIV,XV", "XII,XIII")
    UNKNOWN_LW_CHARS = (".", "?")

    # Roman numerals used by Saenger
    # both in our model and RNAView
    ROMAN_NUMERALS = ("I", "V", "X")

    def __init__(self) -> None:
        self.residues_from_pdb: Dict[int, Residue] = {}
        self.analysis_output = BaseInteractions([], [], [], [], [])

    @classmethod
    def run_rnaview(cls, file_content: str) -> str:
        with tempfile.TemporaryDirectory() as directory_name:
            with tempfile.NamedTemporaryFile(
                "w+", dir=directory_name, suffix=".pdb"
            ) as file:
                file.write(file_content)
                file.seek(0)
                run_external_cmd(["rnaview", file.name], cwd=directory_name)
                with open(f"{file.name}.out", encoding="utf-8") as rnaview_file:
                    rnaview_result = rnaview_file.read()
        logger.debug(f"rnaview result: {rnaview_result}")
        return rnaview_result

    def append_residues_from_pdb_using_rnaview_indexing(self, pdb_content: str) -> None:
        potential_residues: Dict[str, RNAViewAdapter.PotentialResidue] = {}

        for line in pdb_content.splitlines():
            if line.startswith(self.ATOM) or line.startswith(self.HETATM):
                atom_name = line[self.ATOM_NAME_INDEX].strip()

                number = int(line[self.NUMBER_INDEX].strip())
                icode = (
                    None
                    if line[self.ICODE_INDEX].strip() == ""
                    else line[self.ICODE_INDEX]
                )
                chain = line[self.CHAIN_INDEX].strip()
                name = line[self.NAME_INDEX].strip()

                residue = Residue(None, ResidueAuth(chain, number, icode, name))

                if str(residue) not in potential_residues:
                    potential_residues[str(residue)] = RNAViewAdapter.PotentialResidue(
                        residue, None, None, None, None
                    )
                potential_residue = potential_residues[str(residue)]

                atom_position = (
                    float(line[self.X_INDEX].strip()),
                    float(line[self.Y_INDEX].strip()),
                    float(line[self.Z_INDEX].strip()),
                )

                if atom_name == self.ATOM_C6:
                    potential_residue.position_c6 = atom_position
                elif atom_name == self.ATOM_C2:
                    potential_residue.position_c2 = atom_position
                elif atom_name == self.ATOM_N1:
                    potential_residue.position_n1 = atom_position
                elif atom_name == self.ATOM_N9:
                    potential_residue.position_n9 = atom_position

        counter = 1
        for potential_residue in potential_residues.values():
            if potential_residue.is_correct_according_to_rnaview():
                self.residues_from_pdb[counter] = potential_residue.residue
                counter += 1

    def get_leontis_westhof(
        self, lw_info: str, trans_cis_info: str
    ) -> Optional[LeontisWesthof]:
        trans_cis = trans_cis_info[0]
        if any(char in lw_info for char in self.UNKNOWN_LW_CHARS):
            return None
        if lw_info in (
            self.PLUS_INTERACTION,
            self.MINUS_INTERACTION,
            self.X_INTERACTION,
        ):
            return LeontisWesthof[f"{trans_cis}WW"]
        return LeontisWesthof[f"{trans_cis}{lw_info[0].upper()}{lw_info[2].upper()}"]

    def append_interaction(self, rnaview_regex_result: Tuple[str, ...]) -> None:
        residue_left = self.residues_from_pdb[int(rnaview_regex_result[0])]
        residue_right = self.residues_from_pdb[int(rnaview_regex_result[1])]

        # Interaction OR Saenger OR n/a OR empty string
        token = rnaview_regex_result[13]

        if rnaview_regex_result[9] == self.STACKING:
            self.analysis_output.stackings.append(
                Stacking(residue_left, residue_right, None)
            )

        elif token == self.BASE_RIBOSE:
            self.analysis_output.baseRiboseInteractions.append(
                BaseRibose(residue_left, residue_right, None)
            )

        elif token == self.BASE_PHOSPHATE:
            self.analysis_output.basePhosphateInteractions.append(
                BasePhosphate(residue_left, residue_right, None)
            )

        elif token in (self.OTHER_INTERACTION, self.ONE_HBOND):
            self.analysis_output.otherInteractions.append(
                OtherInteraction(residue_left, residue_right)
            )

        elif token == self.SAENGER_UNKNOWN:
            leontis_westhof = self.get_leontis_westhof(
                rnaview_regex_result[10], rnaview_regex_result[11]
            )
            if leontis_westhof is None:
                self.analysis_output.otherInteractions.append(
                    OtherInteraction(residue_left, residue_right)
                )
            else:
                self.analysis_output.basePairs.append(
                    BasePair(residue_left, residue_right, leontis_westhof, None)
                )

        elif (
            all(char in self.ROMAN_NUMERALS for char in token)
            or token in self.DOUBLE_SAENGER
        ):
            leontis_westhof = self.get_leontis_westhof(
                rnaview_regex_result[10], rnaview_regex_result[11]
            )
            if leontis_westhof is None:
                self.analysis_output.otherInteractions.append(
                    OtherInteraction(residue_left, residue_right)
                )
            else:
                saenger = (
                    Saenger[token.split(",", 1)[0]]
                    if token in self.DOUBLE_SAENGER
                    else Saenger[token]
                )
                self.analysis_output.basePairs.append(
                    BasePair(residue_left, residue_right, leontis_westhof, saenger)
                )

        else:
            raise PdbParsingError(f"Unknown RNAView interaction: {token}")

    def check_indexing_correctness(self, regex_result: Tuple[str, ...], line: str) -> None:
        residue_left = self.residues_from_pdb[int(regex_result[0])]

        if residue_left.auth.chain.lower() != regex_result[2].lower() or residue_left.auth.number != int(regex_result[3]):
            raise PdbParsingError(
                f"Wrong internal index for {residue_left}. Fix RNAView internal index mapping. Line: {line}"
            )

        residue_right = self.residues_from_pdb[int(regex_result[1])]

        if residue_right.auth.chain.lower() != regex_result[7].lower() or residue_right.auth.number != int(regex_result[6]):
            raise PdbParsingError(
                f"Wrong internal index for {residue_right}. Fix RNAView internal index mapping. Line: {line}"
            )

    def analyze_by_rnaview(
        self, file_content: str, **_: Dict[str, Any]
    ) -> BaseInteractions:
        self.append_residues_from_pdb_using_rnaview_indexing(file_content)
        rnaview_result = RNAViewAdapter.run_rnaview(file_content)

        base_pair_section = False
        for line in rnaview_result.splitlines():
            if line.startswith(self.BEGIN_BASE_PAIR):
                base_pair_section = True
            elif line.startswith(self.END_BASE_PAIR):
                base_pair_section = False
            elif base_pair_section:
                rnaview_regex_result = re.search(self.RNAVIEW_REGEX, line)
                if rnaview_regex_result is None:
                    raise RegexError("RNAView regex failed")
                rnaview_regex_groups = rnaview_regex_result.groups()
                self.check_indexing_correctness(rnaview_regex_groups, line)
                self.append_interaction(rnaview_regex_groups)

        return self.analysis_output


def analyze(file_content: str, **kwargs: Dict[str, Any]) -> BaseInteractions:
    return RNAViewAdapter().analyze_by_rnaview(file_content, **kwargs)


def main() -> None:
    structure = analyze(sys.stdin.read())
    print(orjson.dumps(structure).decode("utf-8"))


if __name__ == "__main__":
    main()
