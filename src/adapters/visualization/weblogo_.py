#! /usr/bin/env python

# IMPORTANT! this file cannot be named weblogo.py, because it imports from "weblogo", and Python complains about that
# Weblogo (docs: https://weblogo.readthedocs.io/en/latest)
# Requires pdf2svg (repo: https://github.com/dawbarton/pdf2svg)
# Requires svg-stack (repo: https://github.com/astraw/svg_stack)
# Requires ghostscript (website: https://www.ghostscript.com)

import os
import shutil
import subprocess
import tempfile
import uuid
import sys
from collections import defaultdict
from typing import DefaultDict, List, Tuple
from io import StringIO

import weblogo as w
import svg_stack

from adapters.visualization.model import ModelMulti2D


class WeblogoDrawer:

    BASE_RULES = (
        w.SymbolColor('U', 'black', 'neutral'),
        w.SymbolColor('Z', 'black', 'neutral'),
        w.SymbolColor('()', 'gray', 'neutral'),
        w.SymbolColor('[]', 'green', 'neutral'),
        w.SymbolColor('{}', 'blue', 'neutral'),
        w.SymbolColor('<>', 'red', 'neutral'),
    )

    ALPHABET = w.Alphabet('UZ()[]{}<>', [])

    LOGO_OPTIONS = w.LogoOptions(
        show_fineprint=False,
        color_scheme=w.ColorScheme(BASE_RULES, alphabet=ALPHABET),
        unit_name='probability',
        yaxis_label='probability',
        title_fontsize=12,
        stacks_per_line=80,
    )

    def convert_to_fasta(self, data: ModelMulti2D) -> DefaultDict[str, str]:
        strands_structures: DefaultDict[str, str] = defaultdict(str)

        for adapter_result in data.results:
            for strand in adapter_result.strands:
                strands_structures[strand.name] += '>\n' + strand.structure + '\n'

        return strands_structures

    def replace_unreadable_characters(self, fasta: str) -> str:
        return fasta.replace('.', 'U').replace('-', 'Z')

    def generate_weblogo(self, title: str, fasta: str) -> Tuple[w.LogoData, w.LogoFormat]:
        sequence_list = w.read_seq_data(StringIO(fasta), alphabet=self.ALPHABET)

        logo_data = w.LogoData.from_seqs(sequence_list)
        self.LOGO_OPTIONS.logo_title = f'Strand {title}'
        logo_format = w.LogoFormat(logo_data, self.LOGO_OPTIONS)

        return logo_data, logo_format

    def save_to_svg(self, logo_data: w.LogoData, logo_format: w.LogoFormat) -> str:
        """ Makes EPS -> SVG conversion through PDF """

        eps_bytes = w.eps_formatter(logo_data, logo_format)

        # Important: we have to escape some characters to the needs of PostScript
        for patch in (('(()', '(\\()'), ('())', '(\\))')):
            eps_bytes = eps_bytes.replace(patch[0].encode(), patch[1].encode())

        ghost_script = w.GhostscriptAPI()

        pdf_bytes = ghost_script.convert('pdf', eps_bytes.decode(), logo_format.logo_width, logo_format.logo_height)

        command = shutil.which('pdf2svg')
        if command is None:
            raise EnvironmentError('"pdf2svg" software not found. Please install it.')

        with tempfile.TemporaryDirectory() as directory_name:
            with tempfile.NamedTemporaryFile('wb+', dir=directory_name, suffix='.pdf') as temp_pdf:
                temp_pdf.write(pdf_bytes)
                temp_pdf.seek(0)
                file_name = os.path.join(directory_name, f'{str(uuid.uuid4())}.svg')
                subprocess.run(
                    [command, temp_pdf.name, file_name],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
            if not os.path.isfile(file_name):
                raise RuntimeError(f'File "{file_name}" does not exist - "pdf2svg" conversion failed!')
            with open(file_name, 'r', encoding='utf-8') as svg_file:
                svg_result = svg_file.read()

        return svg_result

    def merge_svg_files(self, svg_contents: List[str]) -> str:
        with tempfile.TemporaryDirectory() as directory:
            svg_files: List[str] = []

            for svg_content in svg_contents:
                svg_file_path = os.path.join(directory, f'{str(uuid.uuid4())}.svg')
                svg_files.append(svg_file_path)
                with open(svg_file_path, 'w', encoding='utf-8') as svg_file:
                    svg_file.write(svg_content)

            document = svg_stack.Document()
            layout = svg_stack.VBoxLayout()

            for file in svg_files:
                layout.addSVG(file, alignment=svg_stack.AlignLeft)

            layout.setSpacing(50)
            document.setLayout(layout)
            output_file = os.path.join(directory, f'{str(uuid.uuid4())}.svg')
            document.save(output_file)

            with open(output_file, 'r', encoding='utf-8') as file:
                merged_svg = file.read()

        return merged_svg

    def visualize(self, data: ModelMulti2D) -> str:
        strands_in_fasta_format = self.convert_to_fasta(data)

        svg_files = []
        for strand_name, strand_fasta in strands_in_fasta_format.items():
            modified_strand_fasta = self.replace_unreadable_characters(strand_fasta)
            logo_data, logo_format = self.generate_weblogo(strand_name, modified_strand_fasta)
            svg_content = self.save_to_svg(logo_data, logo_format)
            svg_files.append(svg_content)

        svg_result = self.merge_svg_files(svg_files)
        return svg_result


def main() -> None:
    drawer = WeblogoDrawer()
    fasta = sys.stdin.read()
    modified_fasta = drawer.replace_unreadable_characters(fasta)
    logo_data, logo_format = drawer.generate_weblogo('', modified_fasta)
    svg_content = drawer.save_to_svg(logo_data, logo_format)
    print(svg_content)


if __name__ == '__main__':
    main()
