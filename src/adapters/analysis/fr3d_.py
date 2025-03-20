#! /usr/bin/env python
# IMPORTANT! this file cannot be named fr3d.py, because it imports from "fr3d", and Python complains about that
import logging
import os
import sys
import tempfile
from typing import Any, Dict, List, Tuple

import orjson
from rnapolis.common import (
    BR,
    BaseInteractions,
    BasePair,
    BasePhosphate,
    BaseRibose,
    BPh,
    LeontisWesthof,
    OtherInteraction,
    Residue,
    ResidueAuth,
    Stacking,
    StackingTopology,
)

from adapters.config import config
from adapters.tools.maxit import cif2mmcif
from adapters.tools.utils import run_external_cmd

logger = logging.getLogger(__name__)


def parse_unit_id(nt: str) -> Residue:
    fields = nt.split("|")
    icode = fields[7] if len(fields) >= 8 and fields[7] != "" else None
    auth = ResidueAuth(fields[2], int(fields[4]), icode, fields[3])
    return Residue(None, auth)


def unify_classification(fr3d_name: str) -> tuple:
    original_name = fr3d_name  # Keep for logging

    # Handle 'n' prefix (e.g., ncWW -> cWW, ns55 -> s55)
    if fr3d_name.startswith("n"):
        fr3d_name = fr3d_name[1:]
        logger.debug(
            f"Detected 'n' prefix: removed from {original_name} -> {fr3d_name}"
        )

    # Handle alternative base pairs with 'a' suffix (e.g., cWWa -> cWW)
    if len(fr3d_name) >= 3 and fr3d_name.endswith("a"):
        fr3d_name = fr3d_name[:-1]  # Remove the 'a' suffix
        logger.debug(
            f"Detected alternative base pair: removed 'a' suffix from {original_name} -> {fr3d_name}"
        )

    # Handle backbone interactions: 0BR, 1BR, ... 9BR for base-ribose
    if len(fr3d_name) == 3 and fr3d_name[1:] == "BR" and fr3d_name[0].isdigit():
        try:
            br_type = int(fr3d_name[0])
            return ("base-ribose", BR[br_type])
        except (ValueError, KeyError):
            logger.debug(f"Unknown base-ribose interaction: {original_name}")
            return ("other", None)

    # Handle backbone interactions: 0BPh, 1BPh, ... 9BPh for base-phosphate
    if len(fr3d_name) == 4 and fr3d_name[1:] == "BPh" and fr3d_name[0].isdigit():
        try:
            bph_type = int(fr3d_name[0])
            return ("base-phosphate", BPh[bph_type])
        except (ValueError, KeyError):
            logger.debug(f"Unknown base-phosphate interaction: {original_name}")
            return ("other", None)

    # Handle the stacking notation from direct FR3D service (s33, s35, s53, s55)
    if (
        len(fr3d_name) == 3
        and fr3d_name.startswith("s")
        and fr3d_name[1] in ("3", "5")
        and fr3d_name[2] in ("3", "5")
    ):
        if fr3d_name == "s33":
            return ("stacking", StackingTopology.downward)
        if fr3d_name == "s55":
            return ("stacking", StackingTopology.upward)
        if fr3d_name == "s35":
            return ("stacking", StackingTopology.outward)
        if fr3d_name == "s53":
            return ("stacking", StackingTopology.inward)

    # Handle the cWW style notation from direct FR3D service output
    # Support both uppercase and lowercase edge names (e.g., cWW, cww, tHS, ths, tSs, etc.)
    if len(fr3d_name) == 3 and fr3d_name[0].lower() in ("c", "t"):
        try:
            # Convert to the format expected by LeontisWesthof
            edge_type = fr3d_name[0].lower()  # c or t
            edge1 = fr3d_name[1].upper()  # W, H, S (convert to uppercase)
            edge2 = fr3d_name[2].upper()  # W, H, S (convert to uppercase)

            lw_format = f"{edge_type}{edge1}{edge2}"
            return ("base-pair", LeontisWesthof[lw_format])
        except KeyError:
            logger.debug(
                f"Fr3d unknown interaction from service: {original_name} -> {fr3d_name}"
            )
            return ("other", None)

    # Handle other classifications with different formatting
    logger.debug(f"Fr3d unknown interaction: {fr3d_name}")
    return ("other", None)


def _process_interaction_line(
    line: str,
    category: str,
    interactions_data: Dict[str, list],
):
    """
    Process a single interaction line and add it to the appropriate list.

    Args:
        line: The tab-separated interaction line
        category: The category of interaction (for logging purposes)
        interactions_data: Dictionary containing all interaction lists

    Returns:
        True if successfully processed, False otherwise
    """
    try:
        # Split by tabs and get the first three fields
        parts = line.split("\t")
        if len(parts) < 3:
            logger.warning(f"Invalid {category} line format: {line}")
            return False

        nt1 = parts[0]
        interaction_type = parts[1]
        nt2 = parts[2]

        nt1_residue = parse_unit_id(nt1)
        nt2_residue = parse_unit_id(nt2)

        # Convert the interaction type to our internal format
        interaction_category, classification = unify_classification(interaction_type)

        # Add to the appropriate list based on the interaction category
        if interaction_category == "base-pair":
            interactions_data["base_pairs"].append(
                BasePair(nt1_residue, nt2_residue, classification, None)
            )
        elif interaction_category == "stacking":
            interactions_data["stackings"].append(
                Stacking(nt1_residue, nt2_residue, classification)
            )
        elif interaction_category == "base-ribose":
            interactions_data["base_ribose_interactions"].append(
                BaseRibose(nt1_residue, nt2_residue, classification)
            )
        elif interaction_category == "base-phosphate":
            interactions_data["base_phosphate_interactions"].append(
                BasePhosphate(nt1_residue, nt2_residue, classification)
            )
        elif interaction_category == "other":
            interactions_data["other_interactions"].append(
                OtherInteraction(nt1_residue, nt2_residue)
            )

        return True
    except (ValueError, IndexError) as e:
        logger.warning(f"Error parsing {category} interaction: {e}")
        return False


def run_fr3d_script(mmcif_content: str) -> Tuple[List[str], List[str], List[str]]:
    """
    Run the FR3D Python 2.7 script to analyze RNA structure.

    Args:
        mmcif_content: The mmCIF file content as a string

    Returns:
        Tuple of (basepair_lines, stacking_lines, backbone_lines)
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Write the mmCIF file to the temporary directory
        cif_path = os.path.join(tmpdir, "fr3d.cif")
        with open(cif_path, "w") as f:
            f.write(mmcif_content)

        # Run the FR3D script
        cmd = [
            "/py27_env/bin/python",
            "/py27_env/lib/python2.7/site-packages/fr3d/classifiers/NA_pairwise_interactions.py",
            "-i", tmpdir, "-o", tmpdir, "-c", "basepair,basepair_detail,stacking,backbone", "fr3d"
        ]

        try:
            result = run_external_cmd(
                cmd,
                cwd=tmpdir,
                timeout=config["SUBPROCESS_DEFAULT_TIMEOUT"],
            )
            logger.debug(f"FR3D script exit code: {result.returncode}")

            # Read the output files
            basepair_file = os.path.join(tmpdir, "fr3d_basepair_detail.txt")
            stacking_file = os.path.join(tmpdir, "fr3d_stacking.txt")
            backbone_file = os.path.join(tmpdir, "fr3d_backbone.txt")

            basepair_lines = []
            stacking_lines = []
            backbone_lines = []

            if os.path.exists(basepair_file):
                with open(basepair_file, "r") as f:
                    basepair_lines = f.read().splitlines()

            if os.path.exists(stacking_file):
                with open(stacking_file, "r") as f:
                    stacking_lines = f.read().splitlines()

            if os.path.exists(backbone_file):
                with open(backbone_file, "r") as f:
                    backbone_lines = f.read().splitlines()

            return basepair_lines, stacking_lines, backbone_lines

        except Exception as e:
            logger.error(f"Error running FR3D script: {e}")
            return [], [], []


def analyze(file_content: str, **_: Dict[str, Any]) -> BaseInteractions:
    # Convert to mmCIF format if needed
    mmcif_content = cif2mmcif(file_content)

    # Run the FR3D script
    basepair_lines, stacking_lines, backbone_lines = run_fr3d_script(mmcif_content)

    # Initialize the interaction data dictionary
    interactions_data = {
        "base_pairs": [],
        "stackings": [],
        "base_ribose_interactions": [],
        "base_phosphate_interactions": [],
        "other_interactions": [],
    }

    # Process base pair interactions
    for line in basepair_lines:
        if line.strip() and not line.startswith("#"):
            _process_interaction_line(line, "basepair", interactions_data)

    # Process stacking interactions
    for line in stacking_lines:
        if line.strip() and not line.startswith("#"):
            _process_interaction_line(line, "stacking", interactions_data)

    # Process backbone interactions
    for line in backbone_lines:
        if line.strip() and not line.startswith("#"):
            _process_interaction_line(line, "backbone", interactions_data)

    # Return a BaseInteractions object with all the processed interactions
    return BaseInteractions(
        interactions_data["base_pairs"],
        interactions_data["stackings"],
        interactions_data["base_ribose_interactions"],
        interactions_data["base_phosphate_interactions"],
        interactions_data["other_interactions"],
    )


def main():
    result = analyze(sys.stdin.read())
    print(orjson.dumps(result).decode("utf-8"))


if __name__ == "__main__":
    main()
