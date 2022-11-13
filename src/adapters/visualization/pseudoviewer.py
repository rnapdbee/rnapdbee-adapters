#! /usr/bin/env python

import subprocess
import tempfile
import os

from adapters.visualization.model import ModelMulti2D


class PseudoViewerDrawer:

    def generate_pseudoviewer_svg(self) -> str:
        with tempfile.TemporaryDirectory() as directory:
            with tempfile.NamedTemporaryFile('w+', dir=directory, suffix='.seq') as seqeunce:
                with tempfile.NamedTemporaryFile('w+', dir=directory, suffix='.str') as structure:
                    seqeunce.write('1\nGUCCUCCGGGAU')
                    seqeunce.seek(0)
                    structure.write('1\n((((....))))')
                    structure.seek(0)
                    out_file = os.path.join(directory, 'out.svg')
                    subprocess.run(
                        ['ipy', 'pseudoviewer/PVWrapper.py', seqeunce.name, structure.name, out_file],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=False,
                    )
                    if not os.path.isfile(out_file):
                        raise RuntimeError('SVG does not exist!')
                    with open(out_file, 'r') as file:
                        svg_content = file.read()
        return svg_content

    def visualize(self, data: ModelMulti2D):
        return self.generate_pseudoviewer_svg()


def main() -> None:
    pass


if __name__ == '__main__':
    main()
