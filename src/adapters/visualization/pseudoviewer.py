#! /usr/bin/env python

import os
import re
import sys
import logging
from collections import deque, defaultdict
from typing import Tuple, List, DefaultDict, Deque, Dict
from dataclasses import dataclass
from tempfile import NamedTemporaryFile, TemporaryDirectory

from lxml import etree as ET

from adapters.visualization.model import Model2D, Residue, SYMBOLS, SymbolType
from adapters.tools.utils import run_external_cmd
from adapters.exceptions import RegexError, InvalidSvgError, ThirdPartySoftwareError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PseudoviewerInteraction:
    residue_left: Residue
    residue_right: Residue
    color: str


class PseudoViewerDrawer:

    COLORS = {
        ']': '#2E7012',  # 1st order
        '}': '#0F205F',  # 2nd order
        '>': '#831300',  # 3rd order
        'a': '#550B5B',  # 4th order
        'b': '#4A729D',  # 5th order
        'c': '#8B7605',  # 6th order
        'd': '#C565CF',  # 7th order
        'e': '#9FB925',  # 8th order
        '-': 'red',  # Missing residue
        'NOT_REPRESENTED': 'gray'  # Not represented in dotbracket
    }

    RES_NUMBER_REGEX_1 = re.compile(r'mOver\(evt,.*\(([0-9]+)\).*')
    RES_NUMBER_REGEX_2 = re.compile(r"mOver\(evt,'([0-9]+)'.*")
    XML_NS = '{http://www.w3.org/2000/svg}'

    def __init__(self) -> None:
        self.interactions: List[PseudoviewerInteraction] = []
        self.missing_residues: List[Residue] = []
        self.modified_structure: str
        self.modified_sequence: str
        self.data: Model2D
        self.svg_result: str
        self.elements_mapping: Dict[Tuple[str, int], ET.Element] = {}

    def get_letter_sequence(self, ascii_offset: int, length: int) -> str:
        return chr(97 + ascii_offset) * length

    def get_ascii_offset(self, text: str) -> int:
        return ord(text) - 97

    def has_no_pairs(self, structure: str) -> bool:
        unique_chars = set(structure)
        if len(unique_chars) == 1 or unique_chars == {'.', '-'}:
            return True
        return False

    def parse_strands(self) -> None:
        modified_structure: List[str] = []
        modified_sequence: List[str] = []
        residue_stack: DefaultDict[str, Deque[Residue]] = defaultdict(deque)

        for strand_index, strand in enumerate(self.data.strands):
            strand_name, structure, sequence = strand.name, strand.structure, strand.sequence
            if self.has_no_pairs(structure):
                raise ThirdPartySoftwareError(f'No pairs in strand {strand_name}, PseudoViewer image cannot be drawn')
            modified_sequence.append('1\n')
            modified_structure.append('1\n')
            for char, name, i in zip(structure, sequence, range(len(structure))):
                symbol = SYMBOLS[char]
                number = i + 1
                if symbol.allowed:
                    modified_structure.append(char)
                else:
                    modified_structure.append('.')
                    if char == '-':
                        self.missing_residues.append(Residue(strand_name, number, name))
                    else:
                        if symbol.type == SymbolType.BEGIN:
                            residue_stack[char].append(Residue(strand_name, number, name))
                        else:
                            self.interactions.append(
                                PseudoviewerInteraction(
                                    residue_stack[symbol.sibling].pop(),  # type: ignore
                                    Residue(strand_name, number, name),
                                    self.COLORS[char],
                                ))
            modified_sequence.append(f'{self.get_letter_sequence(strand_index, len(sequence))}\n')
            modified_structure.append('\n')

        self.modified_structure = ''.join(modified_structure)
        self.modified_sequence = ''.join(modified_sequence)

    def append_not_represented_interactions(self) -> None:
        all_residues: Dict[str, Dict[int, int]] = {}
        for chain_with_residues in self.data.chainsWithResidues:
            chain = chain_with_residues.name
            residues = chain_with_residues.residues
            all_residues[chain] = {}
            for i, residue in enumerate(residues):
                all_residues[chain][residue.number] = i + 1

        not_represented = self.data.nonCanonicalInteractions.notRepresented

        for pair in not_represented:
            res_left = pair.residueLeft
            res_right = pair.residueRight

            res_left_mapped = Residue(
                res_left.chain,
                all_residues[res_left.chain][res_left.number],
                res_left.name,
            )

            res_right_mapped = Residue(
                res_right.chain,
                all_residues[res_right.chain][res_right.number],
                res_right.name,
            )

            self.interactions.append(
                PseudoviewerInteraction(
                    res_left_mapped,
                    res_right_mapped,
                    self.COLORS['NOT_REPRESENTED'],
                ))

    def generate_pseudoviewer_svg(self) -> None:
        with TemporaryDirectory() as directory:
            with NamedTemporaryFile('w+', dir=directory, suffix='.seq') as seqeunce_file:
                with NamedTemporaryFile('w+', dir=directory, suffix='.str') as structure_file:
                    seqeunce_file.write(self.modified_sequence)
                    seqeunce_file.seek(0)
                    structure_file.write(self.modified_structure)
                    structure_file.seek(0)
                    output_file = os.path.join(directory, 'out.svg')
                    run_external_cmd(
                        ['pseudoviewer', seqeunce_file.name, structure_file.name, output_file],
                        cwd=directory,
                    )
                    if not os.path.isfile(output_file):
                        raise FileNotFoundError('PseudoViewer image was not created!')
                    with open(output_file, 'r', encoding='utf-8') as file:
                        svg_content = file.read()
                    if 'svg' not in svg_content:
                        raise InvalidSvgError('PseudoViewer image is not a valid SVG!')
        logger.debug(f'PseudoViewer svg: {svg_content}')
        self.svg_result = svg_content

    def color_missing_residues(self) -> None:
        for missing_residue in self.missing_residues:
            key = (missing_residue.chain, missing_residue.number)
            element = self.elements_mapping[key]
            element.set('fill', self.COLORS['-'])

    def color_interactions(self, parent_container: ET.Element) -> None:
        for interaction in self.interactions:
            color = interaction.color
            res_left = interaction.residue_left
            res_right = interaction.residue_right
            element_left = self.elements_mapping[(res_left.chain, res_left.number)]
            element_right = self.elements_mapping[(res_right.chain, res_right.number)]

            x1, y1 = element_left.get('x'), element_left.get('y')
            x2, y2 = element_right.get('x'), element_right.get('y')

            line = ET.Element(
                f'{self.XML_NS}line',
                attrib={
                    'x1': str(float(x1) + 2.4),
                    'y1': str(float(y1) - 2.4),
                    'x2': str(float(x2) + 2.4),
                    'y2': str(float(y2) - 2.4),
                    'stroke': color,
                },
            )

            if color == self.COLORS['NOT_REPRESENTED']:
                line.set('stroke-dasharray', '5,5')

            parent_container.insert(0, line)

    def remove_dashed_lines(self, lines: List[ET.Element]) -> None:
        for dashed_line in lines:
            dashed_line.clear()

    def remove_javascript(self, root: ET.Element, residues_elements: List[ET.Element]) -> None:
        root.remove(root.find(f'.//{self.XML_NS}script'))

        for residue_element in residues_elements:
            residue_element.attrib.pop("onmouseover")
            residue_element.attrib.pop("onmouseout")

    def preprocess(self) -> None:
        self.parse_strands()
        self.append_not_represented_interactions()

    def postprocess(self) -> None:
        root = ET.XML(self.svg_result.encode('utf-8'))

        residues_elements = root.findall(f'.//{self.XML_NS}text[@onmouseover]')
        parent_container = root.find(f'.//{self.XML_NS}g[@transform]')
        dashed_lines = parent_container.findall(f'.//{self.XML_NS}g[@stroke-dasharray]')

        # Connect chain and number of residue with ET.Element
        for res_element in residues_elements:
            mapped_chain = res_element.text
            chain_index = self.get_ascii_offset(mapped_chain)
            chain = self.data.strands[chain_index].name

            residue_info = res_element.get('onmouseover')
            if residue_info.count('(') > 1:
                regex_result = re.search(self.RES_NUMBER_REGEX_1, residue_info)
            else:
                regex_result = re.search(self.RES_NUMBER_REGEX_2, residue_info)

            if regex_result is None:
                raise RegexError("PseudoViewer residue number regex failed!")
            number = int(regex_result.groups()[0])

            self.elements_mapping[(chain, number)] = res_element
            res_element.text = self.data.strands[chain_index].sequence[number - 1]

        self.remove_dashed_lines(dashed_lines)
        self.color_missing_residues()
        self.color_interactions(parent_container)
        self.remove_javascript(root, residues_elements)

        self.svg_result = ET.tostring(root, encoding='unicode', method='xml')

    def visualize(self, data: Model2D) -> str:
        self.data = data

        self.preprocess()
        self.generate_pseudoviewer_svg()
        self.postprocess()

        return self.svg_result


def main() -> None:
    drawer = PseudoViewerDrawer()
    print("Read sequence:")
    drawer.modified_sequence = '1\n' + sys.stdin.read()
    print("Read structure:")
    drawer.modified_structure = '1\n' + sys.stdin.read()
    drawer.generate_pseudoviewer_svg()
    print(drawer.svg_result)


if __name__ == '__main__':
    main()
