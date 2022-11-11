#! /usr/bin/env python

import subprocess
import tempfile
import os

from adapters.visualization.model import ModelMulti2D


class RChieDrawer:

    RCHIE_ARGS = [
        'rchie.R',
        'file.dbn',
        '--format1',
        'vienna',
        '--rule1',
        '6',
        '--colour1',
        '#808080,#8F0000,#007200,#052060,#5D005D,#3C739D,#8F7600,#D25FD2,#9FB925',
        '--pdf',
        '--output',
    ]

    def generate_rchie_svg(self, dotBracket: str) -> str:
        with tempfile.TemporaryDirectory() as directory:
            with tempfile.NamedTemporaryFile('w+', dir=directory, suffix='.dbn') as file:
                file.write(dotBracket)
                file.seek(0)
                output_pdf = os.path.join(directory, 'out.pdf')
                output_svg = os.path.join(directory, 'out.svg')
                subprocess.run(
                    [self.RCHIE_ARGS[0]] + [file.name] + self.RCHIE_ARGS[2:] + [output_pdf],
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
