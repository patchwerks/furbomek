"""Real stage CLI recomputes optical calibration and cannot publish authority."""

import json
import subprocess
import sys
from pathlib import Path

import pytest


def source(view: int = 0) -> Path:
    return Path(__file__).resolve().parents[1] / "fixtures" / f"stage-{view}.json"


def invoke(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(Path(__file__).parents[1] / "stage.py"),
            "--verify",
            str(path),
            "--at-ms",
            "10000",
        ],
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize("view", [0, 1])
def test_real_cli_replays_independently_calibrated_layout(view: int) -> None:
    result = invoke(source(view))
    assert result.returncode == 0, result.stdout + result.stderr
    receipt = json.loads(result.stdout)
    assert receipt["status"] == "REPLAY_ELIGIBLE"
    assert (
        receipt["profile_id"]
        == json.loads(source().read_bytes())["request"]["context"]["stage"][
            "profile_id"
        ]
    )
    assert receipt["physical_motion_authorized"] is False


@pytest.mark.parametrize(
    ("path", "value", "reason"),
    [
        (
            ("calibration_input", "current", "boundary_visible"),
            False,
            "boundary_feet_or_contact_unverified",
        ),
        (
            ("calibration_input", "containment_verified"),
            False,
            "containment_unverified",
        ),
        (
            ("calibration_input", "measurement_uncertainty_mm"),
            6.0,
            "independent_error_exceeds_threshold",
        ),
        (
            ("calibration_input", "current", "camera_revision"),
            "camera-moved",
            "camera_or_reference_revision_changed",
        ),
        (
            ("calibration_receipt", "translation_error_mm"),
            0.01,
            "calibration_receipt_mismatch",
        ),
        (
            ("request", "context", "calibration", "independent_validation_sha256"),
            "0" * 64,
            "calibration_evidence_mismatch",
        ),
        (("request", "current", "start", "x_mm"), 80.0, "current_pose_mismatch"),
        (
            ("request", "context", "calibration", "stage_frame_id"),
            "moved-reference",
            "calibration_identity_mismatch",
        ),
        (
            ("request", "context", "calibration", "translation_error_mm"),
            0.1,
            "calibration_bounds_mismatch",
        ),
        (
            ("request", "context", "calibration", "valid_until_ms"),
            20000,
            "calibration_freshness_mismatch",
        ),
        (("request", "comparison_id"), None, "synthetic_requires_named_replay"),
        (("request", "mode"), "observation_check", "synthetic_requires_named_replay"),
    ],
)
def test_cli_holds_invalid_or_unbound_optical_evidence(
    tmp_path: Path,
    path: tuple[str, ...],
    *,
    value: str | float | bool | None,
    reason: str,
) -> None:
    raw = json.loads(source().read_bytes())
    cursor = raw
    for key in path[:-1]:
        cursor = cursor[key]
    cursor[path[-1]] = value
    destination = tmp_path / "stage.json"
    _ = destination.write_text(json.dumps(raw))
    result = invoke(destination)
    assert result.returncode == 2, result.stderr
    assert reason in json.loads(result.stdout)["reasons"]


def test_cli_missing_stage_holds(tmp_path: Path) -> None:
    result = invoke(tmp_path / "absent.json")
    assert result.returncode == 2
    assert json.loads(result.stdout)["reasons"] == ["stage_evidence_missing_or_invalid"]
