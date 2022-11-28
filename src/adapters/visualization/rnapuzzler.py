#! /usr/bin/env python

import subprocess
import os
import sys
from tempfile import TemporaryDirectory, NamedTemporaryFile

from adapters.visualization.model import Model2D


class RNAPuzzlerDrawer:

    ALLOWED_SYMBOLS = {'.', '(', ')'}

    # Do not modify this value, this file is named by RNAplot
    OUTPUT_SVG = 'rna.svg'

    def remove_forbidden_symbols(self, text: str) -> str:
        replaced_input = []
        for char in text:
            if char in self.ALLOWED_SYMBOLS:
                replaced_input.append(char)
            else:
                replaced_input.append('.')
        return ''.join(replaced_input)

    def generate_rnapuzzler_svg(self, sequence_structure: str) -> str:
        if os.path.isfile(self.OUTPUT_SVG):
            os.remove(self.OUTPUT_SVG)

        with TemporaryDirectory() as directory:
            with NamedTemporaryFile('w+', dir=directory, suffix='.dbn') as input_file:
                input_file.write(sequence_structure)
                input_file.seek(0)
                subprocess.run(
                    ['RNAplot', '-i', input_file.name, '-t', '4', '-o', 'svg'],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                    check=False,
                )
        if not os.path.isfile(self.OUTPUT_SVG):
            raise RuntimeError('RNAPuzzler image was not created!')
        with open(self.OUTPUT_SVG, 'r', encoding='utf-8') as file:
            svg_content = file.read()
        os.remove(self.OUTPUT_SVG)
        if 'svg' not in svg_content:
            raise RuntimeError('RNAPuzzler image is not a valid SVG!')

        return svg_content

    def visualize(self, data: Model2D) -> None:
        joined_sequence = ''.join(tuple(strand.sequence for strand in data.strands))
        joined_structure = ''.join(tuple(strand.structure for strand in data.strands))
        clear_structure = self.remove_forbidden_symbols(joined_structure)
        return self.generate_rnapuzzler_svg(f'{joined_sequence}\n{clear_structure}')


def main() -> None:
    drawer = RNAPuzzlerDrawer()
    sequence_structure = sys.stdin.read()
    print(drawer.generate_rnapuzzler_svg(sequence_structure))


if __name__ == '__main__':
    main()
