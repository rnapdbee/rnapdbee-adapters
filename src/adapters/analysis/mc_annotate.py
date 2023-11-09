#! /usr/bin/env python

import logging
import re
import subprocess
import sys
import tempfile
from enum import Enum
from typing import Any, Dict, List, Tuple, Union

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
    StackingTopology,
)

from adapters.exceptions import PdbParsingError, RegexError
from adapters.tools.utils import run_external_cmd

logger = logging.getLogger(__name__)


class MCAnnotateAdapter:
    # Represents state of parsing MC-Annotate result
    # Luckily every important part of file
    # begins with a unique sentence
    class ParseState(str, Enum):
        RESIDUES_INFORMATION = "Residue conformations"
        ADJACENT_STACKINGS = "Adjacent stackings"
        NON_ADJACENT_STACKINGS = "Non-Adjacent stackings"
        BASE_PAIRS_SECTION = "Base-pairs"
        SUMMARY_SECTION = "Number of"

    # This dictionary maps our model edges
    # to edge representation used by MC-Annotate
    EDGES: Dict[str, Tuple[str, ...]] = {
        "H": ("Hh", "Hw", "Bh", "C8"),
        "W": ("Wh", "Ww", "Ws"),
        "S": ("Ss", "Sw", "Bs"),
    }

    # Contains flatten EDGES values (in one touple)
    ALL_EDGES = sum(EDGES.values(), ())

    # Based on these tokens
    # BaseRiboseInteractions and BasePhosphateInteractions are created
    RIBOSE_ATOM = "O2'"
    PHOSPHATE_ATOM = "O2P"

    # Single hydrogen bond - for us it's OtherInteraction
    ONE_HBOND = "one_hbond"

    # Cis/trans tokens used by MC-Annotate
    CIS = "cis"
    TRANS = "trans"

    # Tokens used in PDB files
    ATOM = "ATOM"
    HETATM = "HETATM"

    # This regex is used to capture 6 groups of residues information:
    # (1) (2) (3) (4) (5) (6)
    # 1, 4 - chain IDs
    # 2, 5 - numbers
    # 3, 6 - icodes (or empty string if no icode)
    # Example - match and groups:
    # A-100.X-B200
    # ('A'), ('-100'), ('X'), ('B'), ('200'), ('')
    RESIDUE_REGEX = re.compile(
        r"'?(.)'?(-?[0-9]+)\.?([a-zA-Z]?)-'?(.)'?(-?[0-9]+)\.?([a-zA-Z]?)"
    )

    # Roman numerals used by Saenger
    # both in our model and MC-Annotate
    ROMAN_NUMERALS = ("I", "V", "X")

    # Positions of resiudes info in PDB files
    CHAIN_INDEX = 21
    NUMBER_INDEX = slice(22, 26)
    ICODE_INDEX = 26
    NAME_INDEX = slice(17, 20)

    def __init__(self) -> None:
        self.analysis_output = BaseInteractions([], [], [], [], [])
        # Since names are not present in adjacent and non-adjacent stackings
        # we need save these values eariler
        self.names: Dict[str, str] = {}

    def classify_edge(self, edge_type: str) -> str:
        for edge, edges in self.EDGES.items():
            if edge_type in edges:
                return edge
        raise PdbParsingError('Edge type "{type}" unknown')

    def get_resiude(self, residue_info_list: Tuple[Union[str, Any], ...]) -> Residue:
        chain = residue_info_list[0]
        number = int(residue_info_list[1])

        if residue_info_list[2] == "":
            icode = None
            residue_info = f"{chain}{number}"
        else:
            icode = residue_info_list[2]
            residue_info = f"{chain}{number}.{icode}"

        return Residue(
            None, ResidueAuth(chain, number, icode, self.names[residue_info])
        )

    def get_residues(self, residues_info: str) -> Tuple[Residue, Residue]:
        regex_result = re.search(self.RESIDUE_REGEX, residues_info)
        if regex_result is None:
            raise RegexError("MC-Annotate regex failed: {residues_info}")
        residues_info_list = regex_result.groups()
        # Expects (chain1, number1, icode1, chain2, number2, icode2)
        if len(residues_info_list) != 6:
            raise RegexError(f"MC-Annotate regex failed for {residues_info}")
        residue_left = self.get_resiude(residues_info_list[:3])
        residue_right = self.get_resiude(residues_info_list[3:])
        return residue_left, residue_right

    def append_stacking(self, line: str, topology_position: int) -> None:
        splitted_line = line.split()
        topology_info = splitted_line[topology_position]
        residue_left, residue_right = self.get_residues(splitted_line[0])
        stacking = Stacking(
            residue_left, residue_right, StackingTopology[topology_info]
        )
        self.analysis_output.stackings.append(stacking)

    def get_ribose_interaction(
        self, residues: Tuple[Residue, Residue], token: str
    ) -> BaseRibose:
        # BasePair is preffered first so swap if necessary
        if token.split("/", 1)[0] == self.RIBOSE_ATOM:
            residue_left, residue_right = residues[1], residues[0]
        else:
            residue_left, residue_right = residues[0], residues[1]
        return BaseRibose(residue_left, residue_right, None)

    def get_phosphate_interaction(
        self, residues: Tuple[Residue, Residue], token: str
    ) -> BasePhosphate:
        # BasePair is preffered first so swap if necessary
        if token.split("/", 1)[0] == self.PHOSPHATE_ATOM:
            residue_left, residue_right = residues[1], residues[0]
        else:
            residue_left, residue_right = residues[0], residues[1]
        return BasePhosphate(residue_left, residue_right, None)

    def get_base_interaction(
        self,
        residues: Tuple[Residue, Residue],
        token: str,
        tokens: List[str],
    ) -> BasePair:
        if self.CIS in tokens:
            cis_trans = "c"
        elif self.TRANS in tokens:
            cis_trans = "t"
        else:
            raise PdbParsingError(f"Cis/trans expected, but not present in {tokens}")

        # example saenger: XIX or XII,XIII (?)
        for potential_saenger_token in tokens:
            potential_saenger_without_comma = potential_saenger_token.split(",")[0]
            if all(
                char in self.ROMAN_NUMERALS for char in potential_saenger_without_comma
            ):
                saenger = Saenger[potential_saenger_without_comma]
                break
        else:
            saenger = None

        left_edge, right_edge = token.split("/", 1)
        leontis_westhof_left = self.classify_edge(left_edge)
        leontis_westohf_right = self.classify_edge(right_edge)
        leontis_westhof = LeontisWesthof[
            f"{cis_trans}{leontis_westhof_left}{leontis_westohf_right}"
        ]
        residue_left, residue_right = residues
        return BasePair(residue_left, residue_right, leontis_westhof, saenger)

    def get_other_interaction(
        self, residues: Tuple[Residue, Residue]
    ) -> OtherInteraction:
        return OtherInteraction(residues[0], residues[1])

    def append_interactions(self, line: str) -> None:
        splitted_line = line.split()
        residues = self.get_residues(splitted_line[0])
        # Assumes that one pair can belong to every interaction type
        # no more than once!
        base_added, ribose_added, phosphate_added = False, False, False
        # example tokens: Ww/Ww pairing antiparallel cis XX
        tokens: List[str] = splitted_line[3:]

        # Special case
        # IF single hydrogen bond and base pairs only THEN
        # append to OtherIneraction list
        if self.ONE_HBOND in tokens:
            for token in tokens:
                if self.RIBOSE_ATOM in token or self.PHOSPHATE_ATOM in token:
                    break
            else:
                other_interaction = self.get_other_interaction(residues)
                self.analysis_output.otherInteractions.append(other_interaction)
                return

        for token in tokens:
            if self.RIBOSE_ATOM in token and not ribose_added:
                # example token: Ss/O2'
                ribose_interaction = self.get_ribose_interaction(residues, token)
                self.analysis_output.baseRiboseInteractions.append(ribose_interaction)
                ribose_added = True

            elif self.PHOSPHATE_ATOM in token and not phosphate_added:
                # example token: O2P/Bh
                phosphate_interaction = self.get_phosphate_interaction(residues, token)
                self.analysis_output.basePhosphateInteractions.append(
                    phosphate_interaction
                )
                phosphate_added = True

            elif len(token.split("/", 1)) > 1:
                token_left, token_right = token.split("/", 1)
                tokens_in_edges = (
                    token_left in self.ALL_EDGES and token_right in self.ALL_EDGES
                )
                if tokens_in_edges and not base_added:
                    # example token_left: Ww | example token_right: Ws
                    base_pair_interaction = self.get_base_interaction(
                        residues, token, tokens
                    )
                    self.analysis_output.basePairs.append(base_pair_interaction)
                    base_added = True

    @classmethod
    def run_mc_annotate(cls, pdb_content: str) -> str:
        with tempfile.TemporaryDirectory() as directory_name:
            with tempfile.NamedTemporaryFile(
                "w+", dir=directory_name, suffix=".pdb"
            ) as file:
                file.write(pdb_content)
                file.seek(0)
                mc_result = run_external_cmd(
                    ["mc-annotate", file.name],
                    cwd=directory_name,
                    stdout=subprocess.PIPE,
                ).stdout.decode("utf-8")
        logger.debug(f"MC-Annotate result: {mc_result}")
        return mc_result

    def append_names(self, file_content: str) -> None:
        for line in file_content.splitlines():
            if line.startswith(self.ATOM) or line.startswith(self.HETATM):
                chain = line[self.CHAIN_INDEX].strip()
                number = line[self.NUMBER_INDEX].strip()
                icode = line[self.ICODE_INDEX].strip()
                name = line[self.NAME_INDEX].strip()
                residue_info = (
                    f"{chain}{number}" if icode == "" else f"{chain}{number}.{icode}"
                )
                self.names[residue_info] = name

    def analyze_by_mc_annotate(
        self, pdb_content: str, **_: Dict[str, Any]
    ) -> BaseInteractions:
        self.append_names(pdb_content)
        mc_result = self.run_mc_annotate(pdb_content)
        current_state = None

        for line in mc_result.splitlines():
            for state in self.ParseState:
                if line.startswith(state.value):
                    current_state = state
                    break
            # Loop ended without break - parse file
            else:
                if current_state == self.ParseState.RESIDUES_INFORMATION:
                    # example line: X7.H : G C3p_endo anti
                    # Skip residues information - meaningless information
                    pass
                elif current_state == self.ParseState.ADJACENT_STACKINGS:
                    # example line: X4.E-X5.F : adjacent_5p upward
                    self.append_stacking(line, 3)
                elif current_state == self.ParseState.NON_ADJACENT_STACKINGS:
                    # example line: Y40.M-Y67.N : inward pairing
                    self.append_stacking(line, 2)
                elif current_state == self.ParseState.BASE_PAIRS_SECTION:
                    # example line: Y38.K-Y51.X : A-U Ww/Ww pairing antiparallel cis XX
                    self.append_interactions(line)
                elif current_state == self.ParseState.SUMMARY_SECTION:
                    # example line: Number of non adjacent stackings = 26
                    # Skip summary section - meaningless information
                    pass

        return self.analysis_output


def analyze(file_content: str, **kwargs: Dict[str, Any]) -> BaseInteractions:
    return MCAnnotateAdapter().analyze_by_mc_annotate(file_content, **kwargs)


def main() -> None:
    analysis_output = analyze(sys.stdin.read())
    print(orjson.dumps(analysis_output).decode("utf-8"))


if __name__ == "__main__":
    main()
