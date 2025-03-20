#! /usr/bin/env python
# IMPORTANT! this file cannot be named fr3d.py, because it imports from "fr3d", and Python complains about that
import logging
import sys
from typing import Any, Dict

import orjson
import requests
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

logger = logging.getLogger(__name__)


def parse_unit_id(nt: str) -> Residue:
    fields = nt.split("|")
    icode = fields[7] if len(fields) >= 8 and fields[7] != "" else None
    auth = ResidueAuth(fields[2], int(fields[4]), icode, fields[3])
    return Residue(None, auth)


def unify_classification(fr3d_name: str) -> tuple:
    original_name = fr3d_name  # Keep for logging
    
    # Handle 'n' prefix (e.g., ncWW -> cWW, ns55 -> s55)
    if fr3d_name.startswith('n'):
        fr3d_name = fr3d_name[1:]
        logger.debug(f"Detected 'n' prefix: removed from {original_name} -> {fr3d_name}")
    
    # Handle alternative base pairs with 'a' suffix (e.g., cWWa -> cWW)
    if len(fr3d_name) >= 3 and fr3d_name.endswith('a'):
        fr3d_name = fr3d_name[:-1]  # Remove the 'a' suffix
        logger.debug(f"Detected alternative base pair: removed 'a' suffix from {original_name} -> {fr3d_name}")
    
    # Handle backbone interactions: 0BR, 1BR, ... 9BR for base-ribose
    if len(fr3d_name) == 3 and fr3d_name[1:] == 'BR' and fr3d_name[0].isdigit():
        try:
            br_type = int(fr3d_name[0])
            return ("base-ribose", BR[br_type])
        except (ValueError, KeyError):
            logger.debug(f"Unknown base-ribose interaction: {original_name}")
            return ("other", None)
            
    # Handle backbone interactions: 0BPh, 1BPh, ... 9BPh for base-phosphate
    if len(fr3d_name) == 4 and fr3d_name[1:] == 'BPh' and fr3d_name[0].isdigit():
        try:
            bph_type = int(fr3d_name[0])
            return ("base-phosphate", BPh[bph_type])
        except (ValueError, KeyError):
            logger.debug(f"Unknown base-phosphate interaction: {original_name}")
            return ("other", None)
    
    # Handle the stacking notation from direct FR3D service (s33, s35, s53, s55)
    if len(fr3d_name) == 3 and fr3d_name.startswith('s') and fr3d_name[1] in ('3', '5') and fr3d_name[2] in ('3', '5'):
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
    if len(fr3d_name) == 3 and fr3d_name[0].lower() in ('c', 't'):
        try:
            # Convert to the format expected by LeontisWesthof
            edge_type = fr3d_name[0].lower()  # c or t
            edge1 = fr3d_name[1].upper()  # W, H, S (convert to uppercase)
            edge2 = fr3d_name[2].upper()  # W, H, S (convert to uppercase)
            
            lw_format = f"{edge_type}{edge1}{edge2}"
            return ("base-pair", LeontisWesthof[lw_format])
        except KeyError:
            logger.debug(f"Fr3d unknown interaction from service: {original_name} -> {fr3d_name}")
            return ("other", None)
    
    # Handle other classifications with different formatting
    logger.debug(f"Fr3d unknown interaction: {fr3d_name}")
    return ("other", None)


def _process_interaction_line(
    line: str, category: str, 
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
        parts = line.split('\t')
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


def analyze(file_content: str, **_: Dict[str, Any]) -> BaseInteractions:
    # Call the external FR3D service
    try:
        response = requests.post(
            f"{config['FR3D_SERVICE_URL']}/",
            data=file_content,
            headers={"Content-Type": "text/plain"},
            timeout=300,
        )
        response.raise_for_status()
        result = response.json()
        logger.debug(f"FR3D service response: {result}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling FR3D service: {e}")
        return BaseInteractions([], [], [], [], [])

    # Initialize the interaction data dictionary
    interactions_data = {
        "base_pairs": [],
        "stackings": [],
        "base_ribose_interactions": [],
        "base_phosphate_interactions": [],
        "other_interactions": []
    }

    # Process each category of interactions
    for category, lines in result.items():
        if not isinstance(lines, list):
            continue
            
        for line in lines:
            _process_interaction_line(line, category, interactions_data)

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