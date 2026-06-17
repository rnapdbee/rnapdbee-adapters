# pylint: disable=redefined-outer-name
import json
import logging
from unittest.mock import patch

import pytest  # pylint: disable=import-error

from adapters.visualization.model import (
    Interaction,
    LeontisWesthof,
    Model2D,
    NonCanonicalInteractions,
    Residue,
    Strand,
)
from adapters.visualization.rnapuzzler import RNAPuzzlerDrawer


@pytest.fixture
def sample_model() -> Model2D:
    return Model2D(
        strands=[
            Strand(name="A", sequence="AAAAA", structure="[[[.."),
            Strand(name="B", sequence="AAAAA", structure="..]]]"),
        ],
        residues=[
            Residue(chain="A", number=1, name="A"),
            Residue(chain="A", number=2, name="A"),
            Residue(chain="A", number=3, name="A"),
            Residue(chain="A", number=4, name="A"),
            Residue(chain="A", number=5, name="A"),
            Residue(chain="B", number=1, name="A"),
            Residue(chain="B", number=2, name="A"),
            Residue(chain="B", number=3, name="A"),
            Residue(chain="B", number=4, name="A"),
            Residue(chain="B", number=5, name="A"),
        ],
        chainsWithResidues=[],
        nonCanonicalInteractions=NonCanonicalInteractions(
            notRepresented=[
                Interaction(
                    residueLeft=Residue(chain="A", number=4, name="A"),
                    residueRight=Residue(chain="B", number=2, name="A"),
                    leontisWesthof=LeontisWesthof.cWW,
                )
            ],
            represented=[
                Interaction(
                    residueLeft=Residue(chain="A", number=1, name="A"),
                    residueRight=Residue(chain="B", number=5, name="A"),
                    leontisWesthof=LeontisWesthof.tWH,
                )
            ],
        ),
    )


def test_visualize_calls_cli2rest_with_rnapuzzler_config(sample_model: Model2D) -> None:
    with patch("adapters.visualization.rnapuzzler.cli2rest_run_single") as mock_run:
        mock_run.return_value = "<svg></svg>"

        result = RNAPuzzlerDrawer().visualize(sample_model)

        assert result == "<svg></svg>"
        mock_run.assert_called_once()
        _, kwargs = mock_run.call_args
        assert kwargs["config_name"] == "rnapuzzler"
        assert kwargs["output_file"] == "clean.svg"
        assert kwargs["input_file_extension"] == ".json"


def test_visualize_passes_strands_and_bp_style(sample_model: Model2D) -> None:
    with patch("adapters.visualization.rnapuzzler.cli2rest_run_single") as mock_run:
        RNAPuzzlerDrawer().visualize(sample_model)

        payload = json.loads(mock_run.call_args.kwargs["input_file_content"])
        assert payload["bp_style"] == "lw"
        assert len(payload["strands"]) == 2
        assert payload["strands"][0]["name"] == "A"
        assert payload["strands"][1]["sequence"] == "AAAAA"


def test_visualize_maps_interactions_to_one_based_positions(sample_model: Model2D) -> None:
    with patch("adapters.visualization.rnapuzzler.cli2rest_run_single") as mock_run:
        RNAPuzzlerDrawer().visualize(sample_model)

        payload = json.loads(mock_run.call_args.kwargs["input_file_content"])
        interactions = payload["interactions"]

        assert len(interactions) == 2

        not_represented = next(
            interaction
            for interaction in interactions
            if interaction["lw"] == "cWW"
        )
        assert not_represented["i"] == 4
        assert not_represented["j"] == 7
        assert not_represented["color"] == RNAPuzzlerDrawer.COLORS["NOT_REPRESENTED"]

        represented = next(
            interaction
            for interaction in interactions
            if interaction["lw"] == "tWH"
        )
        assert represented["i"] == 1
        assert represented["j"] == 10
        assert represented["color"] == RNAPuzzlerDrawer.COLORS["]"]


def test_visualize_omits_stackings_and_nucleotide_colors(sample_model: Model2D) -> None:
    with patch("adapters.visualization.rnapuzzler.cli2rest_run_single") as mock_run:
        RNAPuzzlerDrawer().visualize(sample_model)

        payload = json.loads(mock_run.call_args.kwargs["input_file_content"])
        assert "stackings" not in payload
        assert "nucleotide_colors" not in payload


def test_visualize_logs_json_when_config_enabled(
    sample_model: Model2D, caplog: pytest.LogCaptureFixture
) -> None:
    with patch("adapters.visualization.rnapuzzler.cli2rest_run_single"):
        with patch.dict(
            "adapters.visualization.rnapuzzler.config",
            {"RNAPUZZLER_LOG_JSON": True},
        ):
            caplog.set_level(logging.INFO)
            RNAPuzzlerDrawer().visualize(sample_model)

    assert "RNApuzzler JSON payload:" in caplog.text
    logged_payload = json.loads(caplog.records[0].message.split(": ", 1)[1])
    assert logged_payload["bp_style"] == "lw"


def test_visualize_does_not_log_json_when_config_disabled(
    sample_model: Model2D, caplog: pytest.LogCaptureFixture
) -> None:
    with patch("adapters.visualization.rnapuzzler.cli2rest_run_single"):
        with patch.dict(
            "adapters.visualization.rnapuzzler.config",
            {"RNAPUZZLER_LOG_JSON": False},
        ):
            caplog.set_level(logging.INFO)
            RNAPuzzlerDrawer().visualize(sample_model)

    assert "RNApuzzler JSON payload:" not in caplog.text
