#! /usr/bin/env python

import logging
import os
import sys
from collections import defaultdict, deque
from dataclasses import dataclass
from tempfile import TemporaryDirectory
from typing import DefaultDict, Deque, Dict, List, Optional, Tuple

import RNA
from lxml import etree

from adapters.exceptions import ThirdPartySoftwareError
from adapters.visualization.model import SYMBOLS, Model2D, SymbolType

logger = logging.getLogger(__name__)

SVG_NS = "http://www.w3.org/2000/svg"


@dataclass(frozen=True)
class RNAPuzzlerInteraction:
    number_left: int
    number_right: int
    color: str


class RNAPuzzlerDrawer:
    # RNAplot output filename (with -f svg, the default prefix is "rna")
    OUTPUT_SVG = "rna.svg"

    # Normalized RGB colors (space-separated float triples, 0..1 range)
    COLORS = {
        "]": "0.18 0.439 0.071",  # 1st order
        "}": "0.059 0.125 0.373",  # 2nd order
        ">": "0.514 0.075 0",  # 3rd order
        "a": "0.333 0.043 0.357",  # 4th order
        "b": "0.29 0.447 0.616",  # 5th order
        "c": "0.545 0.463 0.02",  # 6th order
        "d": "0.773 0.396 0.812",  # 7th order
        "e": "0.624 0.725 0.145",  # 8th order
        "NOT_REPRESENTED": "0.5 0.5 0.5",  # Not represented in dotbracket
        "-": "1 0 0",  # Missing residue
        "BASE_PAIR": "0 0 0",  # Label for removed () pair
    }

    # RNAPuzzler limitation
    MAX_STRUCTURE_LENGTH = 32767

    def __init__(self) -> None:
        self.interactions: List[RNAPuzzlerInteraction] = []
        self.missing_res_numbers: List[int] = []
        self.modified_structure: str
        self.modified_sequence: str
        self.data: Model2D
        self.svg_content: str

    # ------------------------------------------------------------------
    # Preprocessing (unchanged — prepares sequence, structure, interactions)
    # ------------------------------------------------------------------

    def parse_strands(self) -> None:
        self.modified_sequence = "".join(
            [strand.sequence for strand in self.data.strands]
        )
        structure = "".join([strand.structure for strand in self.data.strands])
        modified_structure: List[str] = []
        residue_stack: DefaultDict[str, Deque[int]] = defaultdict(deque)

        for i, char in enumerate(structure):
            symbol = SYMBOLS[char]
            if symbol.allowed:
                modified_structure.append(char)
            else:
                modified_structure.append(".")
                if char == "-":
                    self.missing_res_numbers.append(i + 1)
                else:
                    if symbol.type == SymbolType.BEGIN:
                        residue_stack[char].append(i + 1)
                    else:
                        self.interactions.append(
                            RNAPuzzlerInteraction(
                                residue_stack[symbol.sibling].pop(),  # type: ignore
                                i + 1,
                                self.COLORS[char],
                            )
                        )

        self.modified_structure = "".join(modified_structure)

    def append_not_represented_interactions(self) -> None:
        all_residues: Dict[str, int] = {}
        for i, res in enumerate(self.data.residues):
            all_residues[str(res)] = i + 1

        for pair in self.data.nonCanonicalInteractions.notRepresented:
            left = pair.residueLeft
            right = pair.residueRight

            number_left_mapped = all_residues[str(left)]
            number_right_mapped = all_residues[str(right)]

            self.interactions.append(
                RNAPuzzlerInteraction(
                    number_left_mapped,
                    number_right_mapped,
                    self.COLORS["NOT_REPRESENTED"],
                )
            )

    def remove_open_close_brackets(self) -> None:
        structure_copy = self.modified_structure
        self.modified_structure = self.modified_structure.replace("()", "..")

        for i, old, new in zip(
            range(len(structure_copy)), structure_copy, self.modified_structure
        ):
            if old != new and old == "(":
                self.interactions.append(
                    RNAPuzzlerInteraction(
                        i + 1,
                        i + 2,
                        self.COLORS["BASE_PAIR"],
                    )
                )

    def preprocess(self) -> None:
        self.parse_strands()
        self.append_not_represented_interactions()
        self.remove_open_close_brackets()

    # ------------------------------------------------------------------
    # SVG generation via RNAplot
    # ------------------------------------------------------------------

    def generate_rnapuzzler_svg(self) -> None:
        """Generate an SVG structure plot using the ViennaRNA Python API with
        the RNApuzzler layout algorithm.

        Uses ``RNA.plot_layout()`` with ``RNA.PLOT_TYPE_PUZZLER`` to compute
        coordinates and ``RNA.plot_structure_svg()`` to write the SVG file.
        """
        seq_len = len(self.modified_sequence)

        if seq_len > self.MAX_STRUCTURE_LENGTH:
            raise ThirdPartySoftwareError(
                f"Maximum structure length ({self.MAX_STRUCTURE_LENGTH}) for RNAPuzzler exceeded"
            )

        # Create RNApuzzler layout using RNA.plot_layout() which internally
        # calls vrna_plot_coords_puzzler_pt() with default options, bypassing
        # the broken SWIG constructor for vrna_plot_options_puzzler_t.
        layout = RNA.plot_layout(
            self.modified_structure, RNA.PLOT_TYPE_PUZZLER
        )

        with TemporaryDirectory() as directory:
            output_file = os.path.join(directory, self.OUTPUT_SVG)

            result = RNA.plot_structure_svg(
                output_file,
                self.modified_sequence,
                self.modified_structure,
                layout,
            )

            if result == 0 or not os.path.isfile(output_file):
                raise ThirdPartySoftwareError(
                    "RNAPuzzler SVG was not created!"
                )

            with open(output_file, "r", encoding="utf-8") as file:
                self.svg_content = file.read()

            if "<svg" not in self.svg_content:
                raise ThirdPartySoftwareError(
                    "RNAPuzzler output is not a valid SVG!"
                )

        logger.debug(f"RNAPuzzler SVG length: {len(self.svg_content)}")

    # ------------------------------------------------------------------
    # Colour helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _color_to_svg(color_str: str) -> str:
        """Convert a space-separated normalised RGB triple (e.g. ``"0.18 0.439 0.071"``)
        to an SVG ``rgb(R,G,B)`` string with 0-255 integer components.
        """
        parts = color_str.split()
        r = int(round(float(parts[0]) * 255))
        g = int(round(float(parts[1]) * 255))
        b = int(round(float(parts[2]) * 255))
        return f"rgb({r},{g},{b})"

    # ------------------------------------------------------------------
    # SVG postprocessing
    # ------------------------------------------------------------------

    def _extract_nucleotide_coords(
        self, root: etree._Element
    ) -> List[Tuple[float, float]]:
        """Return a list of (x, y) coordinates for each nucleotide, extracted
        from the ``<text>`` elements inside the sequence label group.

        The sequence group has a ``translate(-4.6, 4)`` transform that shifts
        text labels so they appear visually centred over the nucleotide
        positions.  The raw ``x``/``y`` attributes on the ``<text>`` elements
        therefore represent the *centre* of each nucleotide — the same
        coordinate space used by backbone paths and base-pair lines.  We
        intentionally do **not** apply the group's translate offset so that
        the returned coordinates can be used directly for interaction lines
        and missing-residue markers that should point to nucleotide centres.
        """
        coords: List[Tuple[float, float]] = []
        seq_group = self._find_seq_group_by_text(root)

        if seq_group is None:
            logger.warning("Could not find sequence text group in SVG")
            return coords

        for text_elem in seq_group.findall(f"{{{SVG_NS}}}text"):
            x = float(text_elem.get("x", "0"))
            y = float(text_elem.get("y", "0"))
            coords.append((x, y))

        if not coords:
            # Try without namespace
            for text_elem in seq_group.findall("text"):
                x = float(text_elem.get("x", "0"))
                y = float(text_elem.get("y", "0"))
                coords.append((x, y))

        return coords

    def _find_seq_group_by_text(self, root: etree._Element) -> Optional[etree._Element]:
        """Find the ``<g>`` group containing nucleotide ``<text>`` labels.

        ViennaRNA emits this group with ``id="seq"`` and
        ``font-family="SansSerif"``.  We first try matching by ``id``, then
        fall back to finding a ``<g>`` that contains ``<text>`` children with
        a ``font-family`` attribute — this covers SVGs where the ``id`` has
        been stripped by optimisers such as *svgcleaner*.
        """
        # Try by id first (standard ViennaRNA output)
        g = root.find(f".//{{{SVG_NS}}}g[@id='seq']")
        if g is None:
            g = root.find(".//g[@id='seq']")
        if g is not None:
            return g

        # Fallback: find <g> with font-family that contains <text> children
        for g in root.iter(f"{{{SVG_NS}}}g"):
            if g.get("font-family") and g.findall(f"{{{SVG_NS}}}text"):
                return g
        for g in root.iter("g"):
            if g.get("font-family") and g.findall("text"):
                return g

        return None

    def _find_main_group(self, root: etree._Element) -> Optional[etree._Element]:
        """Find the main ``<g transform="scale(...) translate(...)">`` group
        that contains all drawing elements."""
        # The main group is a direct child of <svg> that has a transform attribute
        for child in root:
            if child.tag == f"{{{SVG_NS}}}g" or child.tag == "g":
                if child.get("transform"):
                    return child
        return None

    def _find_seq_group(self, main_group: etree._Element) -> Optional[etree._Element]:
        """Find the sequence label group within the main group.

        Tries ``id="seq"`` first, then falls back to a ``<g>`` with
        ``font-family`` that contains ``<text>`` children.
        """
        for child in main_group:
            tag = child.tag
            if (tag == f"{{{SVG_NS}}}g" or tag == "g") and child.get("id") == "seq":
                return child
        # Fallback: <g> with font-family containing <text> children
        for child in main_group:
            tag = child.tag
            if tag == f"{{{SVG_NS}}}g" or tag == "g":
                if child.get("font-family") and (
                    child.findall(f"{{{SVG_NS}}}text") or child.findall("text")
                ):
                    return child
        return None

    def _update_css_styles(self, root: etree._Element) -> None:
        """Modify the ``<style>`` element to change backbone color to light gray
        and base-pair color to black."""
        style_elem = root.find(f".//{{{SVG_NS}}}style")
        if style_elem is None:
            style_elem = root.find(".//style")
        if style_elem is None:
            return

        css = style_elem.text or ""
        # Change backbone from grey to 0.75 gray (rgb(191,191,191))
        css = css.replace(
            "stroke: grey",
            "stroke: rgb(191,191,191)",
        )
        # Change basepairs from red to black
        css = css.replace(
            "stroke: red",
            "stroke: black",
        )
        style_elem.text = css

    def _center_nucleotide_labels(self, seq_group: etree._Element) -> None:
        """Replace ViennaRNA's hard-coded ``translate(-4.6, 4)`` text offset
        with proper SVG text-centering attributes.

        ViennaRNA shifts the entire sequence group by ``translate(-4.6, 4)``
        to approximate visual centering of single-character labels over the
        nucleotide coordinates.  This approximation depends on a specific
        font and size and breaks when the SVG is rendered with different
        fonts.

        Instead, we remove the translate and set ``text-anchor="middle"``
        (horizontal centering) and ``dominant-baseline="central"`` (vertical
        centering) on the group so that each ``<text>`` element is precisely
        centred over its ``(x, y)`` coordinate by the SVG renderer.
        """
        # Remove the translate transform
        if seq_group.get("transform"):
            del seq_group.attrib["transform"]

        # Set centering attributes on the group so all <text> children inherit
        seq_group.set("text-anchor", "middle")
        seq_group.set("dominant-baseline", "central")

    def _add_interaction_lines(
        self,
        main_group: etree._Element,
        seq_group: etree._Element,
        coords: List[Tuple[float, float]],
    ) -> None:
        """Add colored and dashed interaction lines to the SVG.

        Lines are inserted before ``<g id="seq">`` so that nucleotide labels
        render on top of the interaction lines.
        """
        # Find the insertion index (just before seq_group)
        children = list(main_group)
        try:
            insert_idx = children.index(seq_group)
        except ValueError:
            insert_idx = len(children)

        # Create a group for our custom interaction lines
        interactions_group = etree.Element(f"{{{SVG_NS}}}g", attrib={"id": "interactions"})

        for interaction in self.interactions:
            nr_left = interaction.number_left
            nr_right = interaction.number_right
            color = interaction.color

            # Convert from 1-based residue number to 0-based index
            idx_left = nr_left - 1
            idx_right = nr_right - 1

            if idx_left < 0 or idx_left >= len(coords):
                logger.warning(f"Interaction left index {nr_left} out of range")
                continue
            if idx_right < 0 or idx_right >= len(coords):
                logger.warning(f"Interaction right index {nr_right} out of range")
                continue

            x1, y1 = coords[idx_left]
            x2, y2 = coords[idx_right]

            svg_color = self._color_to_svg(color)

            line_attrib = {
                "x1": f"{x1:.3f}",
                "y1": f"{y1:.3f}",
                "x2": f"{x2:.3f}",
                "y2": f"{y2:.3f}",
                "stroke": svg_color,
                "fill": "none",
            }

            if color == self.COLORS["NOT_REPRESENTED"]:
                # Dashed gray line for not-represented interactions
                line_attrib["stroke-width"] = "1.5"
                line_attrib["stroke-dasharray"] = "3 6"
            elif color == self.COLORS["BASE_PAIR"]:
                # Dashed black line for removed () base pairs
                line_attrib["stroke-width"] = "1"
                line_attrib["stroke-dasharray"] = "9 3.01"
                line_attrib["stroke-dashoffset"] = "9"
            else:
                # Solid colored line for higher-order interactions
                line_attrib["stroke-width"] = "1.5"

            line_elem = etree.SubElement(interactions_group, f"{{{SVG_NS}}}line", attrib=line_attrib)

        main_group.insert(insert_idx, interactions_group)

    def _add_missing_residue_markers(
        self,
        main_group: etree._Element,
        seq_group: etree._Element,
        coords: List[Tuple[float, float]],
    ) -> None:
        """Add circle markers at positions of missing residues.

        The ``cmark`` PostScript procedure in the EPS pipeline drew a colored
        circle at each missing residue position.  We replicate this with SVG
        ``<circle>`` elements.
        """
        if not self.missing_res_numbers:
            return

        # Find the insertion index (just before seq_group)
        children = list(main_group)
        try:
            insert_idx = children.index(seq_group)
        except ValueError:
            insert_idx = len(children)

        missing_color = self._color_to_svg(self.COLORS["-"])
        markers_group = etree.Element(f"{{{SVG_NS}}}g", attrib={"id": "missing-residues"})

        for number in self.missing_res_numbers:
            idx = number - 1
            if idx < 0 or idx >= len(coords):
                logger.warning(f"Missing residue index {number} out of range")
                continue

            x, y = coords[idx]
            circle_attrib = {
                "cx": f"{x:.3f}",
                "cy": f"{y:.3f}",
                "r": "10",
                "stroke": missing_color,
                "stroke-width": "1",
                "fill": "none",
            }
            etree.SubElement(markers_group, f"{{{SVG_NS}}}circle", attrib=circle_attrib)

        # Insert before interactions (which is before seq), so rendering order
        # is: backbone, missing markers, interactions, labels
        main_group.insert(insert_idx, markers_group)

    def _split_backbone_at_strand_boundaries(
        self, main_group: etree._Element
    ) -> None:
        """Break backbone polylines at strand boundaries so that multi-chain
        structures show visible gaps between strands.

        RNAplot draws the backbone as one or more ``<polyline>`` elements.
        For multi-strand structures we need to split these polylines at the
        cumulative strand-length boundaries.
        """
        if len(self.data.strands) <= 1:
            return

        # Compute boundary indices (0-based) where strands end
        # E.g. strands of length [10, 20, 15] → boundaries at indices 10, 30
        # meaning: strand 1 is residues 0..9, strand 2 is 10..29, etc.
        boundaries = set()
        cumulative = 0
        for strand in self.data.strands[:-1]:
            cumulative += len(strand.sequence)
            boundaries.add(cumulative)

        # Collect all backbone polylines
        polylines = []
        for child in list(main_group):
            tag = child.tag
            if tag == f"{{{SVG_NS}}}polyline" or tag == "polyline":
                cls = child.get("class", "")
                if "backbone" in cls:
                    polylines.append(child)

        for polyline in polylines:
            points_str = polyline.get("points", "").strip()
            if not points_str:
                continue

            # Parse all coordinate pairs
            point_pairs = points_str.split("\n")
            points: List[Tuple[float, float]] = []
            for pair in point_pairs:
                pair = pair.strip()
                if not pair:
                    continue
                parts = pair.split(",")
                if len(parts) == 2:
                    try:
                        points.append((float(parts[0]), float(parts[1])))
                    except ValueError:
                        continue

            if not points:
                continue

            # Check if any boundary falls within this polyline's point range.
            # We need to figure out which global nucleotide indices this
            # polyline covers.  The polyline ID tells us: "outline" starts
            # at index 0, "outlineN" starts at index N-1 (the previous point
            # is repeated as the first point to ensure continuity).
            polyline_id = polyline.get("id", "outline")
            if polyline_id == "outline":
                start_idx = 0
            else:
                # outlineN -> starts at nucleotide N-1 (repeated from prior)
                # But the first point is the continuity point from the
                # previous segment, so actual nucleotide indices covered
                # start from N-1
                try:
                    n = int(polyline_id.replace("outline", ""))
                    # The polyline "outlineN" starts with nucleotide N-2 as
                    # a continuity point and then N-1, N, N+1, ...
                    # So the global index of point[0] is N-2, point[1] is N-1, etc.
                    start_idx = n - 2
                except ValueError:
                    start_idx = 0

            # Check which boundaries fall within this polyline
            # Each point corresponds to nucleotide at (start_idx + point_index)
            split_indices: List[int] = []
            for local_idx in range(len(points)):
                global_idx = start_idx + local_idx
                if global_idx in boundaries:
                    split_indices.append(local_idx)

            if not split_indices:
                continue

            # Split the polyline at each boundary
            parent_idx = list(main_group).index(polyline)
            main_group.remove(polyline)

            segments: List[List[Tuple[float, float]]] = []
            prev = 0
            for split_idx in split_indices:
                if prev <= split_idx:
                    segments.append(points[prev:split_idx])
                prev = split_idx
            segments.append(points[prev:])

            # Create new polylines for each non-empty segment
            for seg_i, segment in enumerate(reversed(segments)):
                if len(segment) < 2:
                    continue
                pts = "\n".join(f"      {x:.3f},{y:.3f}" for x, y in segment)
                new_poly = etree.Element(f"{{{SVG_NS}}}polyline", attrib={
                    "class": "backbone",
                    "id": f"{polyline_id}_s{len(segments) - 1 - seg_i}",
                    "points": f"\n{pts}\n    ",
                })
                main_group.insert(parent_idx, new_poly)

    def _remove_scripts(self, root: etree._Element) -> None:
        """Remove ``<script>`` elements from the SVG.

        RNAplot embeds JavaScript for interactive toggling and data arrays.
        These are not needed in our pipeline and may confuse downstream
        tools (svgcleaner, Batik, browsers rendering static images).
        """
        for script in root.findall(f".//{{{SVG_NS}}}script"):
            parent = script.getparent()
            if parent is not None:
                parent.remove(script)
        # Also try without namespace
        for script in root.findall(".//script"):
            parent = script.getparent()
            if parent is not None:
                parent.remove(script)

    def _remove_background_rect_onclick(self, root: etree._Element) -> None:
        """Remove the ``onclick`` handler from the background ``<rect>`` since
        we removed the associated script."""
        for rect in root.iter(f"{{{SVG_NS}}}rect"):
            if rect.get("onclick"):
                del rect.attrib["onclick"]
        for rect in root.iter("rect"):
            if rect.get("onclick"):
                del rect.attrib["onclick"]

    def postprocess_svg(self) -> str:
        """Parse the RNAplot SVG output and apply all modifications:

        1. Update CSS styles (backbone → gray, basepairs → black)
        2. Centre nucleotide labels using SVG text-anchor/dominant-baseline
        3. Split backbone polylines at strand boundaries
        4. Add missing-residue circle markers
        5. Add coloured/dashed interaction lines
        6. Remove embedded JavaScript
        7. Return the modified SVG as a string
        """
        root = etree.fromstring(self.svg_content.encode("utf-8"))

        # 1. Update CSS
        self._update_css_styles(root)

        # Find the main drawing group
        main_group = self._find_main_group(root)
        if main_group is None:
            logger.warning("Could not find main <g> group in SVG, returning as-is")
            return self.svg_content

        # Extract nucleotide coordinates (needed for interactions + markers)
        coords = self._extract_nucleotide_coords(root)
        if not coords:
            logger.warning("No nucleotide coordinates found in SVG")

        # Find the seq group (insertion reference point)
        seq_group = self._find_seq_group(main_group)

        # 2. Centre nucleotide labels over their coordinates
        if seq_group is not None:
            self._center_nucleotide_labels(seq_group)

        # 3. Split backbone at strand boundaries
        self._split_backbone_at_strand_boundaries(main_group)

        if seq_group is not None and coords:
            # 4. Add missing-residue markers
            self._add_missing_residue_markers(main_group, seq_group, coords)

            # 5. Add interaction lines
            self._add_interaction_lines(main_group, seq_group, coords)

        # 6. Remove JavaScript
        self._remove_scripts(root)
        self._remove_background_rect_onclick(root)

        return etree.tostring(root, encoding="UTF-8", xml_declaration=True).decode("UTF-8")

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def visualize(self, data: Model2D) -> str:
        self.data = data

        self.preprocess()
        self.generate_rnapuzzler_svg()
        return self.postprocess_svg()


def main() -> None:
    drawer = RNAPuzzlerDrawer()
    print("Read sequence:")
    drawer.modified_sequence = sys.stdin.read()
    print("Read structure:")
    drawer.modified_structure = sys.stdin.read()
    drawer.generate_rnapuzzler_svg()
    print(drawer.svg_content)


if __name__ == "__main__":
    main()
