#! /usr/bin/env python

# Structure consensus logo visualization using logomaker + matplotlib
# Replaces the previous weblogo-based implementation which depended on
# pkg_resources/setuptools, ghostscript, and pdf2svg

import logging
import sys
from collections import Counter, defaultdict
from io import BytesIO, StringIO
from typing import DefaultDict, Dict, List

import logomaker
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from lxml import etree as ET

from adapters.visualization.model import ModelMulti2D

logger = logging.getLogger(__name__)

STACKS_PER_LINE = 80


class WeblogoDrawer:
    COLORS: Dict[str, str] = {
        "U": "#000000",  # Unpaired residue (dot in dotBracket)
        "Z": "#000000",  # Missing residue (dash in extended dotBracket)
        "(": "#808080",  # Base pair
        ")": "#808080",
        "[": "#2E7012",  # 1st order
        "]": "#2E7012",
        "{": "#0F205F",  # 2nd order
        "}": "#0F205F",
        "<": "#831300",  # 3rd order
        ">": "#831300",
        "A": "#550B5B",  # 4th order
        "a": "#550B5B",
        "B": "#4A729D",  # 5th order
        "b": "#4A729D",
        "C": "#8B7605",  # 6th order
        "c": "#8B7605",
        "D": "#C565CF",  # 7th order
        "d": "#C565CF",
        "E": "#9FB925",  # 8th order
        "e": "#9FB925",
    }

    ALPHABET = list(COLORS.keys())

    def convert_to_fasta(self, data: ModelMulti2D) -> DefaultDict[str, str]:
        strands_structures: DefaultDict[str, str] = defaultdict(str)

        for adapter_result in data.results:
            for strand in adapter_result.strands:
                strands_structures[strand.name] += ">\n" + strand.structure + "\n"

        return strands_structures

    def replace_unreadable_characters(self, fasta: str) -> str:
        return fasta.replace(".", "U").replace("-", "Z")

    def _parse_sequences(self, fasta: str) -> List[str]:
        """Parse FASTA-formatted string into a list of sequences."""
        sequences = []
        for line in fasta.strip().splitlines():
            line = line.strip()
            if line.startswith(">") or not line:
                continue
            sequences.append(line)
        return sequences

    def _sequences_to_probability_matrix(
        self, sequences: List[str]
    ) -> pd.DataFrame:
        """Convert a list of equal-length sequences into a probability matrix."""
        if not sequences:
            return pd.DataFrame()

        seq_length = len(sequences[0])
        n_seqs = len(sequences)

        data = np.zeros((seq_length, len(self.ALPHABET)), dtype=float)
        alphabet_index = {char: i for i, char in enumerate(self.ALPHABET)}

        for seq in sequences:
            for pos, char in enumerate(seq):
                if char in alphabet_index:
                    data[pos, alphabet_index[char]] += 1

        data /= n_seqs

        return pd.DataFrame(data, columns=self.ALPHABET)

    def generate_logo_svg(self, title: str, fasta: str) -> str:
        """Generate a sequence logo SVG string from FASTA data."""
        sequences = self._parse_sequences(fasta)
        if not sequences:
            return ""

        prob_matrix = self._sequences_to_probability_matrix(sequences)
        seq_length = len(prob_matrix)

        n_lines = max(1, (seq_length + STACKS_PER_LINE - 1) // STACKS_PER_LINE)

        fig_width = min(seq_length, STACKS_PER_LINE) * 0.3 + 1.5
        fig_height = n_lines * 2.5
        fig, axes = plt.subplots(
            n_lines, 1, figsize=(fig_width, fig_height), squeeze=False
        )

        for i in range(n_lines):
            ax = axes[i, 0]
            start = i * STACKS_PER_LINE
            end = min(start + STACKS_PER_LINE, seq_length)
            chunk = prob_matrix.iloc[start:end].reset_index(drop=True)

            logo = logomaker.Logo(
                chunk,
                ax=ax,
                color_scheme=self.COLORS,
                font_name="DejaVu Sans Mono",
            )

            ax.set_ylabel("probability")
            ax.set_ylim(0, 1)
            ax.set_xlim(-0.5, len(chunk) - 0.5)

            tick_positions = list(range(0, len(chunk), 10))
            ax.set_xticks(tick_positions)
            ax.set_xticklabels([str(start + t + 1) for t in tick_positions])

            if i == 0:
                ax.set_title(f"Strand {title}", fontsize=12)

        plt.tight_layout()

        buffer = BytesIO()
        fig.savefig(buffer, format="svg")
        plt.close(fig)

        buffer.seek(0)
        return buffer.read().decode("utf-8")

    def add_viewbox(self, svg_content: str) -> str:
        root = ET.XML(svg_content.encode("utf-8"))
        width = root.get("width")
        height = root.get("height")

        if width and height:
            # Strip units (e.g., "432pt" -> "432")
            w = width.replace("pt", "").replace("px", "")
            h = height.replace("pt", "").replace("px", "")
            root.set("viewBox", f"0 0 {w} {h}")

        return ET.tostring(root, encoding="unicode", method="xml")

    def merge_svgs(self, svg_contents: List[str]) -> str:
        """Merge multiple SVG strings into a single vertically-stacked SVG."""
        if len(svg_contents) == 1:
            return svg_contents[0]

        svg_elements = []
        total_height = 0.0
        max_width = 0.0
        spacing = 50.0

        for svg_str in svg_contents:
            root = ET.XML(svg_str.encode("utf-8"))
            width_str = root.get("width", "0").replace("pt", "").replace("px", "")
            height_str = root.get("height", "0").replace("pt", "").replace("px", "")

            try:
                w = float(width_str)
                h = float(height_str)
            except ValueError:
                w, h = 500.0, 200.0

            svg_elements.append((root, w, h))
            max_width = max(max_width, w)
            total_height += h

        total_height += spacing * (len(svg_elements) - 1)

        nsmap = {"xlink": "http://www.w3.org/1999/xlink"}
        merged = ET.Element(
            "svg",
            xmlns="http://www.w3.org/2000/svg",
            nsmap=nsmap,
            width=str(max_width),
            height=str(total_height),
            viewBox=f"0 0 {max_width} {total_height}",
        )

        y_offset = 0.0
        for root, w, h in svg_elements:
            group = ET.SubElement(
                merged, "g", transform=f"translate(0,{y_offset})"
            )

            # Copy all children from the original SVG into the group
            for child in root:
                group.append(child)

            y_offset += h + spacing

        return ET.tostring(merged, encoding="unicode", method="xml")

    def visualize(self, data: ModelMulti2D) -> str:
        strands_in_fasta_format = self.convert_to_fasta(data)

        svg_files = []
        for strand_name, strand_fasta in strands_in_fasta_format.items():
            modified_strand_fasta = self.replace_unreadable_characters(strand_fasta)
            svg_content = self.generate_logo_svg(strand_name, modified_strand_fasta)
            if svg_content:
                svg_files.append(svg_content)

        if not svg_files:
            return "<svg xmlns='http://www.w3.org/2000/svg'/>"

        svg_result = self.merge_svgs(svg_files)
        boxed_svg = self.add_viewbox(svg_result)

        return boxed_svg


def main() -> None:
    drawer = WeblogoDrawer()
    fasta = sys.stdin.read()
    modified_fasta = drawer.replace_unreadable_characters(fasta)
    svg_content = drawer.generate_logo_svg("", modified_fasta)
    boxed_svg = drawer.add_viewbox(svg_content)
    print(boxed_svg)


if __name__ == "__main__":
    main()
