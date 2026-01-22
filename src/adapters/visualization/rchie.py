#! /usr/bin/env python
import json
import logging
import os
import sys
from typing import List, Optional, TypedDict

from rnapolis.common import DotBracket, MultiStrandDotBracket

from adapters.cli2rest_client import cli2rest_run_single
from adapters.visualization.model import Model2D

logger = logging.getLogger(__name__)
base_url = os.getenv("CLI2REST_RCHIE_URL", "http://localhost:8000")


class Interaction(TypedDict):
    i: int
    j: int
    color: Optional[str]


class RchieData(TypedDict):
    sequence: str
    title: Optional[str]
    top: List[Interaction]
    bottom: List[Interaction]


class RChieDrawer:
    # Only 8 colors are supported by RChie
    COLORS = {
        "(": "#808080",  # Base pair
        "<": "#831300",  # 3rd order
        "[": "#2E7012",  # 1st order
        "{": "#0F205F",  # 2nd order
        "A": "#550B5B",  # 4th order
        "B": "#4A729D",  # 5th order
        "C": "#8B7605",  # 6th order
        "D": "#C565CF",  # 7th order
    }

    def generate_rchie_svg(self, dot_bracket: DotBracket) -> str:
        interactions: List[Interaction] = []
        for i, j in dot_bracket.pairs:
            interactions.append(
                Interaction(
                    i=i + 1,
                    j=j + 1,
                    color=self.COLORS.get(dot_bracket.structure[i], None),
                )
            )
        data = RchieData(
            sequence=dot_bracket.sequence,
            title="",
            top=interactions,
            bottom=[],
        )

        return cli2rest_run_single(
            base_url=base_url,
            input_file_content=json.dumps(data),
            input_file_extension=".json",
            config_name="rchie",
            output_file="clean.svg",
        )

    def visualize(self, data: Model2D) -> str:
        return self.generate_rchie_svg(
            DotBracket(
                "".join(strand.sequence for strand in data.strands),
                "".join(strand.structure for strand in data.strands),
            )
        )


def main() -> None:
    drawer = RChieDrawer()
    dot_bracket = MultiStrandDotBracket.from_file(sys.argv[1])
    print(drawer.generate_rchie_svg(dot_bracket))


if __name__ == "__main__":
    main()
