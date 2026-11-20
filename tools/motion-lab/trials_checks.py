"""Per-attempt semantic and geometric rejection gates for offline replay."""

import math
from pathlib import Path
from typing import assert_never

from pydantic import ValidationError

from calibration_geometry import CalibrationHoldError
from calibration_images import import_images
from calibration_models import CalibrationInput
from calibration_solver import calibrate
from score import read_observation
from score_models import ScoreInput, ScoreResult
from trials_gateway import cross
from trials_models import Trial


def semantic_axis(trial: Trial) -> tuple[int, int]:
    """Map exact guarded verbs to independent expected body direction."""
    match trial.conditions.action:
        case "forward":
            axis = 0, 1
        case "backward":
            axis = 0, -1
        case "left":
            axis = 1, 1
        case "right":
            axis = 1, -1
        case "turn_left":
            axis = 2, 1
        case "turn_right":
            axis = 2, -1
        case "active":
            axis = 3, 1
        case "sleep":
            axis = 3, -1
        case unreachable:
            assert_never(unreachable)
    return axis


def check_trial(trial: Trial, result: ScoreResult) -> tuple[str, ...]:
    """Refuse ACK-only, wrong direction, mixed motion and insufficient clearance."""
    reasons: list[str] = []
    data, metrics = trial.score, result.metrics
    if data is None or metrics is None:
        return ("optical_measurement_unavailable", *result.reasons)
    if result.outcome != "motion" or result.settled is not True:
        reasons.append("optical_" + result.outcome)
    if data.guard.wire_status != "completed" or not trial.normal_disarm:
        reasons.append("guard_completion_or_disarm_missing")
    if result.slip_evidence != "unmeasurable":
        reasons.append("slip_or_post_stop_drift")
    axis, sign = semantic_axis(trial)
    values = (metrics.x_forward, metrics.y_left, metrics.yaw_ccw, metrics.height_up)
    expected = data.expected
    targets = (
        expected.x_forward_mm,
        expected.y_left_mm,
        expected.yaw_ccw_deg,
        expected.height_up_mm,
    )
    if targets[axis] * sign <= 0 or any(
        v != 0 for i, v in enumerate(targets) if i != axis
    ):
        reasons.append("semantic_target_mismatch")
    if values[axis].value * sign <= values[axis].uncertainty:
        reasons.append("signed_progress_below_error")
    if result.motion_kind == "mixed":
        reasons.append("mixed_motion")
    if (trial.start_pose, trial.end_pose) != (
        trial.conditions.start_pose,
        trial.conditions.end_pose,
    ):
        reasons.append("pose_mismatch")
    if not trial.conditions.surface.covers(trial.observed_surface):
        reasons.append("surface_mismatch")
    stage = trial.stage
    if (
        stage.stage_id != data.calibration.stage_id
        or stage.calibration_id != data.calibration_id
        or stage.robot_revision != trial.conditions.robot_revision
        or stage.installed_sha256 != trial.conditions.installed_sha256
        or stage.surface != trial.observed_surface
        or stage.hazards
    ):
        reasons.append("stage_binding_or_hazards")
    required = (
        trial.conditions.swept_radius_mm
        + metrics.peak_excursion.value
        + metrics.peak_excursion.uncertainty
        + metrics.post_stop_excursion.value
        + metrics.post_stop_excursion.uncertainty
        + trial.conditions.interval_travel_mm
    )
    vertices = stage.usable_polygon.vertices
    clearance = min(
        cross(a, vertices[(i + 1) % len(vertices)], trial.stage_start_mm)
        / math.dist(a, vertices[(i + 1) % len(vertices)])
        for i, a in enumerate(vertices)
    )
    if clearance < required:
        reasons.append("insufficient_independent_clearance")
    bands = trial.conditions.voltage_bands
    if (
        any(a >= b for a, b in bands)
        or any(a <= trial.observed_voltage <= b for a, b in bands) is False
    ):
        reasons.append("voltage_outside_tested_range")
    return tuple(reasons)


def observed_heading(data: ScoreInput, directory: Path) -> float | None:
    """Recover the first scored heading using the scorer's image verification."""
    try:
        first = data.frames[0]
        observation = first.observation
        if (
            data.calibration.provenance == "measured"
            or observation.image_file is not None
        ):
            observation = read_observation(first, directory)
        calibration = import_images(data.calibration, directory)
        calibration = CalibrationInput.model_validate(
            calibration.model_dump() | {"current": observation}
        )
        receipt = calibrate(calibration, observation.captured_ms)
    except (CalibrationHoldError, OSError, ValidationError):
        return None
    return receipt.recovered_poses[-1].yaw_deg if receipt.recovered_poses else None
