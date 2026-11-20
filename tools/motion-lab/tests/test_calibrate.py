"""Observable metric accuracy and fail-closed import/CLI regression coverage."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Literal, assert_never

import cv2
import pytest

from calibration_geometry import CalibrationHoldError
from calibration_images import detect_frame, import_images
from calibration_models import CalibrationInput
from calibration_solver import calibrate
from tests.fixture_scene import image_scene, raster, scene


@pytest.mark.parametrize("view", [0, 1])
def test_independent_distorted_views_recover_metric_pose_and_height(view: int) -> None:
    result = calibrate(scene(view), 10000)
    assert result.status == "CALIBRATED_REPLAY", result.reasons
    assert result.motion_admitted is False
    assert result.translation_error_mm is not None
    assert result.yaw_error_deg is not None
    assert result.translation_error_mm < 0.55
    assert result.yaw_error_deg < 0.25
    final = result.recovered_poses[-1]
    assert (final.x_mm, final.y_mm, final.z_mm, final.yaw_deg) == pytest.approx(
        (45, 65, -65, -20), abs=0.02
    )


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ("size", "printed_dimensions_mismatch"),
        ("baseline", "printed_dimensions_mismatch"),
        ("crop", "boundary_feet_or_contact_unverified"),
        ("feet", "boundary_feet_or_contact_unverified"),
        ("contact", "boundary_feet_or_contact_unverified"),
        ("containment", "containment_unverified"),
        ("rear", "rear_diagnostic_clearance_unqualified"),
        ("camera", "camera_or_reference_revision_changed"),
        ("reference", "camera_or_reference_revision_changed"),
        ("loss", "missing_or_duplicate_markers"),
        ("duplicate", "missing_or_duplicate_markers"),
        ("corner", "cropped_marker"),
        ("bump", "fixed_reference_moved"),
        ("error", "independent_error_exceeds_threshold"),
        ("height", "independent_error_exceeds_threshold"),
        ("uncertainty", "independent_error_exceeds_threshold"),
        ("diversity", "insufficient_intrinsic_view_diversity"),
    ],
)
def test_invalid_observation_holds(
    change: Literal[
        "size",
        "baseline",
        "crop",
        "feet",
        "contact",
        "containment",
        "rear",
        "camera",
        "reference",
        "loss",
        "duplicate",
        "corner",
        "bump",
        "error",
        "height",
        "uncertainty",
        "diversity",
    ],
    reason: str,
) -> None:
    data = scene().model_dump(mode="json")
    match change:
        case "size":
            data["measured_target_side_mm"] = 38
        case "baseline":
            data["measured_baseline_mm"] = 118
        case "crop":
            data["current"]["boundary_visible"] = False
        case "feet":
            data["current"]["all_feet_visible"] = False
        case "contact":
            data["current"]["contact_label"] = "unknown"
        case "containment":
            data["containment_verified"] = False
        case "rear":
            data["setup"] = "rear_diagnostic"
        case "camera":
            data["current"]["camera_revision"] = "changed"
        case "reference":
            data["current"]["reference_revision"] = "changed"
        case "loss":
            _ = data["current"]["markers"].pop(0)
        case "duplicate":
            data["current"]["markers"].append(data["current"]["markers"][0])
        case "corner":
            data["current"]["markers"][0]["corners"][0] = [0, 0]
        case "bump":
            for marker in data["current"]["markers"]:
                marker["corners"] = [[x + 3, y] for x, y in marker["corners"]]
        case "error":
            data["validations"][1]["expected"]["x_mm"] += 10
        case "height":
            data["validations"][1]["expected"]["z_mm"] = 0
        case "uncertainty":
            data["measurement_uncertainty_mm"] = 6
        case "diversity":
            data["intrinsic_views"] = [data["intrinsic_views"][0]] * 8
        case unreachable:
            assert_never(unreachable)
    result = calibrate(CalibrationInput.model_validate(data), 10000)
    assert result.status == "HOLD"
    assert result.reasons == (reason,)


@pytest.mark.parametrize("now", [9999, 10601])
def test_current_frame_must_be_fresh(now: int) -> None:
    assert calibrate(scene(), now).reasons == ("stale_or_future_observation",)


def test_cli_success_dirty_output_and_malformed_input(tmp_path: Path) -> None:
    source = tmp_path / "input.json"
    _ = source.write_text(scene().model_dump_json())
    output = tmp_path / "output"
    command = [
        sys.executable,
        str(Path(__file__).parents[1] / "calibrate.py"),
        "--input",
        str(source),
        "--output",
        str(output),
        "--at-ms",
        "10000",
    ]
    success = subprocess.run(command, capture_output=True, text=True, check=False)
    assert success.returncode == 0, success.stderr
    original = (output / "calibration.json").read_bytes()
    assert json.loads(original)["status"] == "CALIBRATED_REPLAY"
    dirty = subprocess.run(command, capture_output=True, text=True, check=False)
    assert dirty.returncode == 2
    assert json.loads(dirty.stdout)["reasons"] == ["output_already_exists"]
    assert (output / "calibration.json").read_bytes() == original
    _ = source.write_text('{"schema_version":1, "provenance":"measured"}')
    command[command.index("--output") + 1] = str(tmp_path / "invalid")
    invalid = subprocess.run(command, capture_output=True, text=True, check=False)
    assert invalid.returncode == 2
    assert json.loads(invalid.stdout)["status"] == "HOLD"


@pytest.mark.parametrize("view", [0, 1])
def test_raster_tag_detection_and_digest_bound_import(
    tmp_path: Path, view: int
) -> None:

    data = scene(view)
    frame = data.current
    path = tmp_path / "frame.png"
    assert cv2.imwrite(str(path), raster(frame))
    detected = detect_frame(path, frame)
    assert {m.marker_id for m in detected.markers} == {0, 1, 2, 3, 10}
    expected = {m.marker_id: m for m in frame.markers}
    for marker in detected.markers:
        for actual, known in zip(
            marker.corners, expected[marker.marker_id].corners, strict=True
        ):
            assert actual == pytest.approx(known, abs=1)
    bound = frame.model_copy(
        update={
            "image_file": "frame.png",
            "image_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    )
    measured = CalibrationInput.model_validate(
        data.model_dump()
        | {
            "provenance": "measured",
            "intrinsic_views": [bound] * 8,
            "reference": bound,
            "current": bound,
            "validations": [
                v.model_dump() | {"frame": bound} for v in data.validations
            ],
        }
    )
    imported = import_images(measured, tmp_path)
    assert imported.current.markers == detected.markers
    _ = path.write_bytes(b"tampered")
    with pytest.raises(CalibrationHoldError, match="image_digest_mismatch"):
        _ = import_images(measured, tmp_path)


def test_target_outside_surveyed_region_holds() -> None:
    data = scene().model_dump(mode="json")
    data["current"]["markers"][-1]["corners"] = [
        [x + 60, y] for x, y in data["current"]["markers"][-1]["corners"]
    ]
    assert calibrate(CalibrationInput.model_validate(data), 10000).reasons == (
        "outside_validated_region",
    )


@pytest.mark.parametrize("view", [0, 1])
def test_full_image_replay_recovers_known_metric_pose(
    tmp_path: Path, view: int
) -> None:
    data = import_images(image_scene(tmp_path, view), tmp_path)
    result = calibrate(data, 10000)
    assert result.status == "CALIBRATED_REPLAY", result.reasons
    final = result.recovered_poses[-1]
    assert (final.x_mm, final.y_mm, final.z_mm) == pytest.approx((45, 65, -65), abs=2.5)
    assert final.yaw_deg == pytest.approx(-20, abs=1)
