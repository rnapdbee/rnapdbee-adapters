#! /usr/bin/env python

import subprocess
import tempfile
import os

from adapters.visualization.model import ModelMulti2D


class RChieDrawer:

    # Only 8 colors are supported by RChie
    COLORS = {
        '()': '#808080',  # Base pair
        '<>': '#831300',  # 3rd order
        '[]': '#2E7012',  # 1st order
        '{}': '#0F205F',  # 2nd order
        'Aa': '#550B5B',  # 4th order
        'Bb': '#4A729D',  # 5th order
        'Cc': '#8B7605',  # 6th order
        'Dd': '#C565CF',  # 7th order
    }

    def generate_rchie_svg(self, dot_bracket: str) -> str:
        with tempfile.TemporaryDirectory() as directory:
            with tempfile.NamedTemporaryFile('w+', dir=directory, suffix='.dbn') as file:
                file.write(dot_bracket)
                file.seek(0)
                output_pdf = os.path.join(directory, 'out.pdf')
                output_svg = os.path.join(directory, 'out.svg')
                subprocess.run(
                    [
                        'rchie.R',
                        file.name,
                        '--format1',
                        'vienna',
                        '--rule1',
                        '6',
                        '--colour1',
                        ','.join(tuple(self.COLORS.values())),
                        '--pdf',
                        '--output',
                        output_pdf,
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
            subprocess.run(
                ['pdf2svg', output_pdf, output_svg],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            with open(output_svg, 'r', encoding='utf-8') as svg_file:
                svg_content = svg_file.read()
        return svg_content

    def visualize(self, data: ModelMulti2D):
        structure = ''.join([strand.structure for strand in data.results[0].strands])
        return self.generate_rchie_svg(structure)


def main() -> None:
    pass


if __name__ == '__main__':
    main()
