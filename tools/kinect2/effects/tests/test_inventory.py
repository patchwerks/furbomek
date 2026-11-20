# /// script
# requires-python = ">=3.12"
# dependencies = ["pydantic==2.14.3", "pytest==9.0.2"]
# ///
# Run with gateway pytest and PYTHONPATH=tools/kinect2/effects.
"""Protect the catalog's measurement and selection boundaries."""

import subprocess
import sys
from pathlib import Path
from typing import Final

import pytest
from pydantic import ValidationError
from validate_inventory import Capability, Inventory

ROOT: Final = Path(__file__).resolve().parents[1]


def test_rgb_cannot_be_relabelled_measured_depth() -> None:
    result = subprocess.run(  # noqa: S603 - fixed local CLI and adversarial fixture
        [
            sys.executable,
            str(ROOT / "validate_inventory.py"),
            "--fixture",
            "mislabeled-depth",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert '"valid": false' in result.stdout
    assert "measured_depth_requires_depth_input" in result.stdout


@pytest.mark.parametrize(
    ("original", "replacement", "error"),
    [
        ("[512,424]", "[1920,1080]", "native_depth_grid_required"),
        (
            '"origin":"capture"',
            '"origin":"derived"',
            "inference_is_not_sensor_measurement",
        ),
        (
            '"max_measured_depth_samples":217088',
            '"max_measured_depth_samples":2073600',
            "less_than_equal",
        ),
        (
            '"evidence":["services/camera-capture/kinect2.cpp"]',
            '"evidence":[]',
            "too_short",
        ),
    ],
)
def test_catalog_rejects_invalid_measurement_claim(
    original: str,
    replacement: str,
    error: str,
) -> None:
    catalog = Inventory.model_validate_json((ROOT / "inventory.json").read_bytes())
    measured = next(entry for entry in catalog.entries if entry.id == "measured-xyz")
    raw = measured.model_dump_json()
    assert original in raw
    with pytest.raises(ValidationError, match=error):
        _ = Capability.model_validate_json(raw.replace(original, replacement))


def test_duplicate_ids_cannot_ambiguously_select_capability() -> None:
    catalog = Inventory.model_validate_json((ROOT / "inventory.json").read_bytes())
    duplicate = catalog.model_copy(
        update={"entries": (*catalog.entries, catalog.entries[0])}
    )
    with pytest.raises(ValidationError, match="duplicate_capability_id"):
        _ = Inventory.model_validate_json(duplicate.model_dump_json())


def test_valid_catalog_preserves_optical_and_depth_as_distinct() -> None:
    inventory = Inventory.model_validate_json((ROOT / "inventory.json").read_bytes())
    optical = next(
        entry for entry in inventory.entries if entry.id == "crimson-samples"
    )
    measured = next(entry for entry in inventory.entries if entry.id == "measured-xyz")
    assert optical.max_measured_depth_samples == 0
    assert measured.max_measured_depth_samples == 217088
    assert optical.input.resolution == (1920, 1080)
    assert measured.input.resolution == (512, 424)
