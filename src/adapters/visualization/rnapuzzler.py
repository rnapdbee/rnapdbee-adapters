#! /usr/bin/env python

import logging
import os
import sys
from collections import defaultdict, deque
from dataclasses import dataclass
from enum import Enum
from tempfile import TemporaryDirectory
from typing import DefaultDict, Deque, List

from adapters.exceptions import InvalidEpsError, ThirdPartySoftwareError
from adapters.tools.utils import convert_to_svg_using_inkscape, run_external_cmd
from adapters.visualization.model import SYMBOLS, Model2D, SymbolType

logger = logging.getLogger(__name__)


class ParseState(Enum):
    OTHER = 0
    COLORPAIR = 1
    CMARK = 2


@dataclass(frozen=True)
class RNAPuzzlerInteraction:
    number_left: int
    number_right: int
    color: str


class RNAPuzzlerDrawer:
    # Do not modify this value, it's RNAPuzzler name
    # This is EPS file, not PS (it makes a difference for inkscape)
    OUTPUT_EPS = "rna.ps"

    # Paths to PosctScript additional procedures
    DASHED_PAIR_PATH = "/RNAplot/dashed_pair.ps"
    MULTIPLE_STRANDS_PATH = "/RNAplot/multiple_strands.ps"

    # Normalized RGB colors
    COLORS = {
        "]": "0.18 0.439 0.071",  # 1st order
        "}": "0.059 0.125 0.373",  # 2nd order
        ">": "0.514 0.075 0",  # 3rd order
        "a": "0.333 0.043 0.357",  # 4th order
        "b": "0.29 0.447 0.616",  # 5th order
        "c": "0.545 0.463 0.02",  # 6th order
        "d": "0.773 0.396 0.812",  # 7th order
        "e": "0.624 0.725 0.145",  # 8th order
        "NOT_REPRESENTED": "0.5 0.5 0.5",  # Not represented in dotbracket
        "-": "1 0 0",  # Missing residue
        "BASE_PAIR": "0 0 0",  # Label for removed () pair
    }

    # RNAPuzzler limitation
    MAX_STRUCTURE_LENGTH = 32767

    def __init__(self) -> None:
        self.interactions: List[RNAPuzzlerInteraction] = []
        self.missing_res_numbers: List[int] = []
        self.modified_structure: str
        self.modified_sequence: str
        self.data: Model2D
        self.result: str

    def parse_strands(self) -> None:
        self.modified_sequence = "".join(
            [strand.sequence for strand in self.data.strands]
        )
        structure = "".join([strand.structure for strand in self.data.strands])
        modified_structure: List[str] = []
        residue_stack: DefaultDict[str, Deque[int]] = defaultdict(deque)

        for i, char in enumerate(structure):
            symbol = SYMBOLS[char]
            if symbol.allowed:
                modified_structure.append(char)
            else:
                modified_structure.append(".")
                if char == "-":
                    self.missing_res_numbers.append(i + 1)
                else:
                    if symbol.type == SymbolType.BEGIN:
                        residue_stack[char].append(i + 1)
                    else:
                        self.interactions.append(
                            RNAPuzzlerInteraction(
                                residue_stack[symbol.sibling].pop(),  # type: ignore
                                i + 1,
                                self.COLORS[char],
                            )
                        )

        self.modified_structure = "".join(modified_structure)

    def append_not_represented_interactions(self) -> None:
        all_residues = {}
        for i, res in enumerate(self.data.residues):
            all_residues[str(res)] = i + 1

        for pair in self.data.nonCanonicalInteractions.notRepresented:
            left = pair.residueLeft
            right = pair.residueRight

            number_left_mapped = all_residues[str(left)]
            number_right_mapped = all_residues[str(right)]

            self.interactions.append(
                RNAPuzzlerInteraction(
                    number_left_mapped,
                    number_right_mapped,
                    self.COLORS["NOT_REPRESENTED"],
                )
            )

    def remove_open_close_brackets(self) -> None:
        structure_copy = self.modified_structure
        self.modified_structure = self.modified_structure.replace("()", "..")

        for i, old, new in zip(
            range(len(structure_copy)), structure_copy, self.modified_structure
        ):
            if old != new and old == "(":
                self.interactions.append(
                    RNAPuzzlerInteraction(
                        i + 1,
                        i + 2,
                        self.COLORS["BASE_PAIR"],
                    )
                )

    def preprocess(self) -> None:
        self.parse_strands()
        self.append_not_represented_interactions()
        self.remove_open_close_brackets()

    def generate_rnapuzzler_eps(self) -> None:
        input_dbn = f"{self.modified_sequence}\n{self.modified_structure}"

        if (len(input_dbn) - 1) / 2 > self.MAX_STRUCTURE_LENGTH:
            raise ThirdPartySoftwareError(
                f"Maximum structure length ({self.MAX_STRUCTURE_LENGTH}) for RNAPuzzler exceeded"
            )

        with TemporaryDirectory() as directory:
            run_external_cmd(
                ["RNAplot", "-t", "4", "--post", ""],
                cwd=directory,
                cmd_input=input_dbn.encode("utf-8"),
            )
            output_file = os.path.join(directory, self.OUTPUT_EPS)
            if not os.path.isfile(output_file):
                raise FileNotFoundError("RNAPuzzler EPS was not created!")
            with open(output_file, "r", encoding="utf-8") as file:
                eps_content = file.read()
            if "RNAplot" not in eps_content:
                raise InvalidEpsError("RNAPuzzler file is not a valid EPS!")
        logger.debug(f"RNAPuzzler EPS {eps_content}")
        self.result = eps_content

    def draw_interactions(self) -> List[str]:
        lines: List[str] = []

        for interaction in self.interactions:
            nr_left = interaction.number_left
            nr_right = interaction.number_right
            color = interaction.color
            if color == self.COLORS["NOT_REPRESENTED"]:
                lines.append(
                    f'{nr_left} {nr_right} 1.5 [3 6] 0 {self.COLORS["NOT_REPRESENTED"]} dashedpair'
                )
            elif color == self.COLORS["BASE_PAIR"]:
                lines.append(
                    f'{nr_left} {nr_right} 1 [9 3.01] 9 {self.COLORS["BASE_PAIR"]} dashedpair'
                )
            else:
                lines.append(f"{nr_left} {nr_right} {color} colorpair")

        return lines

    def draw_missing_residues(self) -> List[str]:
        lines: List[str] = []

        for number in self.missing_res_numbers:
            lines.append(f"{number} cmark")

        return lines

    def insert_procedures(self) -> List[str]:
        with open(self.DASHED_PAIR_PATH, encoding="utf-8") as file:
            lines = file.read().splitlines()

        return lines

    def read_muliple_strands_procedure(self) -> List[str]:
        with open(self.MULTIPLE_STRANDS_PATH, encoding="utf-8") as file:
            lines = file.read().splitlines()

        return lines

    def insert_strands_array(self) -> str:
        chains_lengths = [str(len(strand.sequence)) for strand in self.data.strands]
        return f'/strands [{" ".join(chains_lengths)}] def'

    def postprocess(self) -> None:
        modified_result: List[str] = []
        in_colorpair = False
        in_draw_outline = False

        for line in self.result.splitlines():
            trim_line = line.strip()

            if trim_line.startswith("/cmark"):
                modified_result.append(line)
                modified_result.append(f'{self.COLORS["-"]} setrgbcolor')

            elif trim_line.startswith("/drawoutline"):
                strands_procedure = self.read_muliple_strands_procedure()
                strands_array = self.insert_strands_array()
                modified_result.append(strands_array)
                modified_result.extend(strands_procedure)
                in_draw_outline = True

            elif in_draw_outline and trim_line.startswith("} bind def"):
                in_draw_outline = False

            elif in_draw_outline and not trim_line.startswith("} bind def"):
                pass

            elif trim_line.startswith("/outlinecolor"):
                modified_result.append("/outlinecolor {0.75 setgray} bind def")

            elif trim_line.startswith("/paircolor"):
                modified_result.append("/paircolor {0 setgray} bind def")

            elif trim_line.startswith("/colorpair"):
                modified_result.append(line)
                in_colorpair = True

            elif in_colorpair and trim_line.startswith("hsb"):
                modified_result.append("setrgbcolor")

            elif in_colorpair and trim_line.startswith("fsize setlinewidth"):
                modified_result.append("1.5 setlinewidth")
                in_colorpair = False

            elif trim_line.startswith("% Start Annotations"):
                modified_result.append(line)
                modified_result.extend(self.draw_interactions())
                modified_result.extend(self.draw_missing_residues())

            elif trim_line.startswith("%%EndProlog"):
                modified_result.extend(self.insert_procedures())
                modified_result.append(line)

            else:
                modified_result.append(line)

        self.result = "\n".join(modified_result)

    def visualize(self, data: Model2D) -> str:
        self.data = data

        self.preprocess()
        self.generate_rnapuzzler_eps()
        self.postprocess()

        return convert_to_svg_using_inkscape(self.result, ".eps")


def main() -> None:
    drawer = RNAPuzzlerDrawer()
    print("Read sequence:")
    drawer.modified_sequence = sys.stdin.read()
    print("Read structure:")
    drawer.modified_structure = sys.stdin.read()
    drawer.generate_rnapuzzler_eps()
    print(convert_to_svg_using_inkscape(drawer.result, ".eps"))


if __name__ == "__main__":
    main()
