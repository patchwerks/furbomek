"""Fail-closed observation qualification from independent metric surveys."""

from typing import assert_never

import cv2
import numpy as np

from calibration_geometry import (
    BASELINE_MM,
    REFERENCE_SIDE_MM,
    TARGET_SIDE_MM,
    CalibrationHoldError,
    camera_pose,
    image_points,
    recover_lens,
    reference_points,
    target_pose,
)
from calibration_models import CalibrationInput, CalibrationResult


def calibrate(data: CalibrationInput, now_ms: int) -> CalibrationResult:
    """Return calibrated observation or a named HOLD; never grant motion."""
    try:
        return qualify(data, now_ms)
    except (cv2.error, np.linalg.LinAlgError):
        return CalibrationResult(
            status="HOLD",
            reasons=("numerical_solver_failed",),
            provenance=data.provenance,
        )
    except CalibrationHoldError as error:
        return CalibrationResult(
            status="HOLD", reasons=(error.reason,), provenance=data.provenance
        )


def qualify(data: CalibrationInput, now_ms: int) -> CalibrationResult:
    """Fit, independently check, and bind the current frame to one fixed site."""
    dimensions = (
        (data.measured_reference_side_mm, REFERENCE_SIDE_MM),
        (data.measured_target_side_mm, TARGET_SIDE_MM),
        (data.measured_baseline_mm, BASELINE_MM),
    )
    if any(abs(measured - expected) > 0.25 for measured, expected in dimensions):
        raise CalibrationHoldError("printed_dimensions_mismatch")
    frames = (data.reference, *(item.frame for item in data.validations), data.current)
    if any(
        frame.camera_revision != data.camera_revision
        or frame.reference_revision != data.reference_revision
        for frame in frames
    ):
        raise CalibrationHoldError("camera_or_reference_revision_changed")
    if not 0 <= now_ms - data.current.captured_ms <= data.maximum_age_ms:
        raise CalibrationHoldError("stale_or_future_observation")
    match data.setup:
        case "rear_diagnostic":
            raise CalibrationHoldError("rear_diagnostic_clearance_unqualified")
        case "clearance":
            pass
        case unreachable:
            assert_never(unreachable)
    if not data.containment_verified:
        raise CalibrationHoldError("containment_unverified")
    if any(
        not frame.boundary_visible
        or not frame.all_feet_visible
        or frame.contact_label != "contact"
        for frame in frames
    ):
        raise CalibrationHoldError("boundary_feet_or_contact_unverified")
    lens = recover_lens(data.intrinsic_views)
    reference_pixels = image_points(data.reference, (0, 1, 2, 3))
    site = camera_pose((reference_points(), reference_pixels), lens)
    for frame in frames[1:]:
        drift = np.linalg.norm(
            image_points(frame, (0, 1, 2, 3)) - reference_pixels, axis=1
        )
        if float(drift.max()) > 1.0:
            raise CalibrationHoldError("fixed_reference_moved")
    poses = tuple(target_pose(item.frame, lens, site) for item in data.validations)
    errors = [
        float(
            np.linalg.norm(
                np.array(
                    [
                        p.x_mm - v.expected.x_mm,
                        p.y_mm - v.expected.y_mm,
                        p.z_mm - v.expected.z_mm,
                    ]
                )
            )
        )
        for p, v in zip(poses, data.validations, strict=True)
    ]
    yaw_errors = [
        abs((p.yaw_deg - v.expected.yaw_deg + 180) % 360 - 180)
        for p, v in zip(poses, data.validations, strict=True)
    ]
    translations = np.array(
        [[v.expected.x_mm, v.expected.y_mm] for v in data.validations]
    )
    if (
        float(np.linalg.norm(np.ptp(translations, axis=0)))
        < data.minimum_translation_mm
        or np.ptp([v.expected.yaw_deg for v in data.validations]) < data.minimum_yaw_deg
    ):
        raise CalibrationHoldError("insufficient_independent_baseline")
    translation_error = max(errors) + data.measurement_uncertainty_mm
    yaw_error = max(yaw_errors) + data.measurement_uncertainty_deg
    if (
        translation_error > 5
        or yaw_error > 2
        or translation_error * 4 >= data.minimum_translation_mm
        or yaw_error * 4 >= data.minimum_yaw_deg
    ):
        raise CalibrationHoldError("independent_error_exceeds_threshold")
    current = target_pose(data.current, lens, site)
    hull = cv2.convexHull(translations.astype(np.float32))
    if (
        cv2.pointPolygonTest(hull, (current.x_mm, current.y_mm), measureDist=True)
        < -translation_error
    ):
        raise CalibrationHoldError("outside_validated_region")
    if (
        not min(p.z_mm for p in poses) - translation_error
        <= current.z_mm
        <= max(p.z_mm for p in poses) + translation_error
    ):
        raise CalibrationHoldError("outside_validated_height")
    match data.provenance:
        case "synthetic":
            status = "CALIBRATED_REPLAY"
        case "measured":
            status = "CALIBRATED_OBSERVATION"
        case unreachable:
            assert_never(unreachable)
    return CalibrationResult(
        status=status,
        provenance=data.provenance,
        translation_error_mm=translation_error,
        yaw_error_deg=yaw_error,
        intrinsic_rms_px=lens.rms,
        camera_matrix=tuple(
            tuple(float(value) for value in row) for row in lens.matrix
        ),
        distortion=tuple(float(value) for value in lens.distortion.flatten()),
        recovered_poses=(*poses, current),
        stage_id=data.stage_id,
        camera_revision=data.camera_revision,
        reference_revision=data.reference_revision,
        reference_to_camera_rotation=tuple(
            tuple(float(v) for v in row) for row in site[0]
        ),
        reference_to_camera_translation_mm=tuple(float(v) for v in site[1].flatten()),
    )
