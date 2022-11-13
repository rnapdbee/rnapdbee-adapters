#! /usr/bin/env python

import subprocess
import tempfile
import os

from adapters.visualization.model import ModelMulti2D


class RNAPuzzlerDrawer:

    # Do not modify this value, this file is named by RNAplot
    OUTPUT_SVG = 'rna.svg'

    def generate_rnapuzzler_svg(self) -> str:
        if os.path.isfile(self.OUTPUT_SVG):
            os.remove(self.OUTPUT_SVG)

        with tempfile.TemporaryDirectory() as directory:
            with tempfile.NamedTemporaryFile('w+', dir=directory, suffix='.dbn') as dot_bracket:
                dot_bracket.write('gCGGAUUUAgCUCAGuuGGGAGAGCgCCAGAcUgAAgAucUGGAGgUCcUGUGuuCGaUCCACAGAAUUCGCACCA' +
                                  '\n(((((((..((((.....[..)))).((((.........)))).....(((((..]....))))))))))))----')
                dot_bracket.seek(0)
                subprocess.run(
                    ['RNAplot', '-i', dot_bracket.name, '-t', '4', '-o', 'svg'],
                    check=True,
                )
        if not os.path.isfile(self.OUTPUT_SVG):
            raise RuntimeError('SVG does not exist!')
        with open(self.OUTPUT_SVG, 'r', encoding='utf-8') as file:
            svg_content = file.read()
        os.remove(self.OUTPUT_SVG)

        return svg_content

    def visualize(self, data: ModelMulti2D):
        return self.generate_rnapuzzler_svg()


def main() -> None:
    pass


if __name__ == '__main__':
    main()
