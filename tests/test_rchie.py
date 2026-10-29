# pylint: disable=redefined-outer-name
import json
import re
from typing import Any, Dict, List
from unittest.mock import patch

import pytest  # pylint: disable=import-error
from rnapolis.common import DotBracket

from adapters.visualization.model import (
    ChainWithResidues,
    Interaction,
    LeontisWesthof,
    Model2D,
    NonCanonicalInteractions,
    Residue,
    Strand,
)
from adapters.visualization.rchie import RChieDrawer

# R accepts colour names and #rgb / #rgba / #rrggbb / #rrggbbaa hex values.
# Anything else (notably CSS functional notation) makes plot.xy() abort the
# whole drawing with "invalid color name".
R_COLOR_PATTERN = re.compile(
    r"^(?:[A-Za-z][A-Za-z0-9 ]*|#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8}))$"
)


@pytest.fixture
def model_with_non_canonical() -> Model2D:
    residues = [Residue(chain="A", number=i, name="A") for i in range(1, 21)]
    return Model2D(
        strands=[Strand(name="A", sequence="A" * 20, structure="." * 20)],
        residues=residues,
        chainsWithResidues=[ChainWithResidues(name="A", residues=residues)],
        nonCanonicalInteractions=NonCanonicalInteractions(
            represented=[],
            notRepresented=[
                Interaction(
                    residueLeft=residues[0],
                    residueRight=residues[-1],
                    leontisWesthof=LeontisWesthof.cWW,
                )
            ],
        ),
    )


def _captured_payload(
    drawer: RChieDrawer, dot_bracket: DotBracket, model: Any = None
) -> Dict[str, Any]:
    """Runs the drawer with the cli2rest call stubbed out and returns the JSON it would send."""
    with patch(
        "adapters.visualization.rchie.cli2rest_run_single", return_value="<svg/>"
    ) as run:
        drawer.generate_rchie_svg(dot_bracket, model)
    payload = run.call_args.kwargs["input_file_content"]
    return json.loads(payload)


def _all_colors(payload: Dict[str, Any]) -> List[str]:
    colors: List[str] = []
    for section in ("top", "bottom"):
        for interaction in payload[section]:
            if interaction.get("color") is not None:
                colors.append(interaction["color"])
    return colors


def test_every_color_is_valid_r_syntax():
    dot_bracket = DotBracket("AAAAA....AAAAA", "((((......))))")

    payload = _captured_payload(RChieDrawer(), dot_bracket)

    colors = _all_colors(payload)
    assert colors, "expected at least one coloured interaction"
    for color in colors:
        assert R_COLOR_PATTERN.match(color), f"R cannot parse colour {color!r}"


def test_canonical_pairs_use_the_documented_palette():
    dot_bracket = DotBracket("AAAAA....AAAAA", "((((......))))")

    payload = _captured_payload(RChieDrawer(), dot_bracket)

    assert {interaction["color"] for interaction in payload["top"]} == {"#808080"}


def test_non_canonical_interactions_use_translucent_black(model_with_non_canonical):
    dot_bracket = DotBracket(
        model_with_non_canonical.strands[0].sequence,
        model_with_non_canonical.strands[0].structure,
    )

    payload = _captured_payload(
        RChieDrawer(), dot_bracket, model=model_with_non_canonical
    )

    colors = _all_colors(payload)
    assert "#00000080" in colors, f"expected translucent black, got {colors}"
    # regression guard: CSS rgba() is not valid R and aborts the R script
    assert not any("rgba(" in color for color in colors)
