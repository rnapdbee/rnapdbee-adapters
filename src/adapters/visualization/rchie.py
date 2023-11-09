#! /usr/bin/env python

import logging
import os
import sys
import tempfile

from adapters.tools.utils import pdf_to_svg, run_external_cmd
from adapters.visualization.model import Model2D

logger = logging.getLogger(__name__)


class RChieDrawer:
    # Only 8 colors are supported by RChie
    COLORS = {
        "()": "#808080",  # Base pair
        "<>": "#831300",  # 3rd order
        "[]": "#2E7012",  # 1st order
        "{}": "#0F205F",  # 2nd order
        "Aa": "#550B5B",  # 4th order
        "Bb": "#4A729D",  # 5th order
        "Cc": "#8B7605",  # 6th order
        "Dd": "#C565CF",  # 7th order
    }

    def generate_rchie_svg(self, dot_bracket: str) -> str:
        with tempfile.TemporaryDirectory() as directory:
            with tempfile.NamedTemporaryFile(
                "w+", dir=directory, suffix=".dbn"
            ) as file:
                file.write(dot_bracket)
                file.seek(0)
                output_pdf = os.path.join(directory, "out.pdf")
                run_external_cmd(
                    [
                        "rchie.R",
                        file.name,
                        "--format1",
                        "vienna",
                        "--rule1",
                        "6",
                        "--colour1",
                        ",".join(tuple(self.COLORS.values())),
                        "--pdf",
                        "--output",
                        output_pdf,
                    ],
                    cwd=directory,
                )
                if not os.path.isfile(output_pdf):
                    raise FileNotFoundError("Rchie PDF was not generated!")
            svg_content = pdf_to_svg(output_pdf)
        logger.debug(f"Rchie svg: {svg_content}")
        return svg_content

    def visualize(self, data: Model2D) -> str:
        structure = "".join(tuple(strand.structure for strand in data.strands))
        return self.generate_rchie_svg(structure)


def main() -> None:
    drawer = RChieDrawer()
    dot_bracket = sys.stdin.read()
    print(drawer.generate_rchie_svg(dot_bracket))


if __name__ == "__main__":
    main()
