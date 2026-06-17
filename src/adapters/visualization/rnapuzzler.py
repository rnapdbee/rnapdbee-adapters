#! /usr/bin/env python
import json
import logging
import os
import sys
from typing import Dict, List, Optional, TypedDict

from adapters.cli2rest_client import cli2rest_run_single
from adapters.visualization.model import Interaction, Model2D, SYMBOLS, SymbolType

logger = logging.getLogger(__name__)
base_url = os.getenv("CLI2REST_RNAPUZZLER_URL", "http://localhost:8000")


class StrandInput(TypedDict):
    name: str
    sequence: str
    structure: str


class InteractionInput(TypedDict):
    i: int
    j: int
    lw: Optional[str]
    color: str


class PuzzlerData(TypedDict):
    bp_style: str
    strands: List[StrandInput]
    interactions: List[InteractionInput]


# pylint: disable=too-few-public-methods
class RNAPuzzlerDrawer:
    # Normalized RGB colors (space-separated float triples, 0..1 range).
    # These mirror the colors used by the cli2rest-rnapuzzler wrapper for
    # bracket-derived non-canonical interactions.
    COLORS = {
        "]": "0.18 0.439 0.071",
        "}": "0.059 0.125 0.373",
        ">": "0.514 0.075 0",
        "a": "0.333 0.043 0.357",
        "b": "0.29 0.447 0.616",
        "c": "0.545 0.463 0.02",
        "d": "0.773 0.396 0.812",
        "e": "0.624 0.725 0.145",
        "NOT_REPRESENTED": "0.5 0.5 0.5",
    }

    def visualize(self, data: Model2D) -> str:
        structure = "".join(strand.structure for strand in data.strands)
        residue_to_position = self._build_residue_to_position(data)

        interactions: List[InteractionInput] = []
        for interaction in data.nonCanonicalInteractions.represented:
            self._append_interaction(
                interactions,
                interaction,
                residue_to_position,
                structure,
                is_not_represented=False,
            )
        for interaction in data.nonCanonicalInteractions.notRepresented:
            self._append_interaction(
                interactions,
                interaction,
                residue_to_position,
                structure,
                is_not_represented=True,
            )

        puzzler_data = PuzzlerData(
            bp_style="lw",
            strands=[
                StrandInput(
                    name=strand.name,
                    sequence=strand.sequence,
                    structure=strand.structure,
                )
                for strand in data.strands
            ],
            interactions=interactions,
        )

        return cli2rest_run_single(
            base_url=base_url,
            input_file_content=json.dumps(puzzler_data),
            input_file_extension=".json",
            config_name="rnapuzzler",
            output_file="clean.svg",
        )

    def _append_interaction(
        self,
        interactions: List[InteractionInput],
        interaction: Interaction,
        residue_to_position: Dict[str, int],
        structure: str,
        is_not_represented: bool,
    ) -> None:
        position_left = residue_to_position.get(str(interaction.residueLeft))
        position_right = residue_to_position.get(str(interaction.residueRight))
        if position_left is None or position_right is None:
            logger.warning(
                "Skipping RNApuzzler interaction with unmapped residue(s): %s",
                interaction,
            )
            return

        interactions.append(
            InteractionInput(
                i=position_left,
                j=position_right,
                lw=self._lw_to_string(interaction.leontisWesthof),
                color=self._resolve_color(
                    structure, position_left, is_not_represented
                ),
            )
        )

    @staticmethod
    def _build_residue_to_position(data: Model2D) -> Dict[str, int]:
        return {str(residue): index + 1 for index, residue in enumerate(data.residues)}

    @staticmethod
    def _lw_to_string(leontis_westhof) -> Optional[str]:
        return leontis_westhof.value if leontis_westhof is not None else None

    def _resolve_color(
        self,
        structure: str,
        position_left: int,
        is_not_represented: bool,
    ) -> str:
        if is_not_represented:
            return self.COLORS["NOT_REPRESENTED"]

        color_key = self._find_bracket_color_key(structure, position_left)
        return self.COLORS.get(color_key, self.COLORS["NOT_REPRESENTED"])

    @staticmethod
    def _find_bracket_color_key(structure: str, position: int) -> Optional[str]:
        """Return the closing-bracket symbol whose color applies to the pair.

        The color palette is keyed by closing brackets (e.g. ``]``, ``}``),
        matching the convention used by the cli2rest-rnapuzzler wrapper.
        """
        symbol_at_position = structure[position - 1]
        symbol_info = SYMBOLS.get(symbol_at_position)
        if symbol_info is None:
            return None

        if symbol_info.type == SymbolType.BEGIN and symbol_info.sibling is not None:
            return symbol_info.sibling

        if symbol_info.type == SymbolType.END:
            return symbol_at_position

        return None


def main() -> None:
    drawer = RNAPuzzlerDrawer()
    with open(sys.argv[1], "r", encoding="utf-8") as file:
        data = Model2D.from_dict(json.load(file))
    print(drawer.visualize(data))


if __name__ == "__main__":
    main()
