"""Verify private stage evidence offline; no capture, actuator or release authority."""

import hashlib
from math import hypot
from pathlib import Path
from typing import assert_never

import cv2
import numpy as np

from calibration_images import import_images
from calibration_models import CalibrationInput, CalibrationResult, Contract
from calibration_solver import calibrate
from stage_gateway import Polygon, StageReceipt, StageRequest, verify_stage


class StageBundle(Contract):
    """Private exact calibration inputs/receipt plus independent stage evidence."""

    request: StageRequest
    calibration_input: CalibrationInput
    calibration_receipt: CalibrationResult


def verify_bundle(bundle: StageBundle, directory: Path, now_ms: int) -> StageReceipt:
    """Recompute optical calibration and check its metric binding before geometry."""
    data = import_images(bundle.calibration_input, directory)
    result = calibrate(data, now_ms)
    result = result.model_copy(
        update={
            "input_sha256": hashlib.sha256(
                bundle.calibration_input.model_dump_json().encode()
            ).hexdigest()
        }
    )
    match result.status:
        case "HOLD":
            return StageReceipt(
                status="HOLD", local_checks_passed=False, reasons=result.reasons
            )
        case "CALIBRATED_REPLAY" | "CALIBRATED_OBSERVATION":
            pass
        case unreachable:
            assert_never(unreachable)
    request = StageRequest.model_validate(
        bundle.request.model_dump()
        | {"context": bundle.request.context.model_dump() | {"now_ms": now_ms}}
    )
    calibration = request.context.calibration
    reasons: list[str] = []
    if result != bundle.calibration_receipt:
        reasons.append("calibration_receipt_mismatch")
    if (
        hashlib.sha256(result.model_dump_json().encode()).hexdigest()
        != calibration.independent_validation_sha256
    ):
        reasons.append("calibration_evidence_mismatch")
    if (
        data.stage_id != calibration.stage_id
        or data.camera_revision != calibration.observation_revision
        or data.reference_revision != calibration.stage_frame_id
    ):
        reasons.append("calibration_identity_mismatch")
    if (
        result.translation_error_mm is None
        or result.yaw_error_deg is None
        or calibration.translation_error_mm < result.translation_error_mm
        or calibration.yaw_error_deg < result.yaw_error_deg
        or calibration.minimum_translation_mm != data.minimum_translation_mm
        or calibration.minimum_yaw_deg != data.minimum_yaw_deg
    ):
        reasons.append("calibration_bounds_mismatch")
    if (
        calibration.valid_from_ms != data.current.captured_ms
        or calibration.valid_until_ms > data.current.captured_ms + data.maximum_age_ms
        or request.current.observed_ms != data.current.captured_ms
    ):
        reasons.append("calibration_freshness_mismatch")
    points = np.array(
        [[v.expected.x_mm, v.expected.y_mm] for v in data.validations], dtype=np.float32
    )
    hull = cv2.convexHull(points).reshape(-1, 2)
    coverage = Polygon(
        vertices=tuple(
            calibration.observation_to_stage.apply((float(x), float(y)))
            for x, y in hull
        )
    )
    if not all(coverage.contains(v) for v in calibration.coverage.vertices):
        reasons.append("coverage_outside_independent_validation")
    current = result.recovered_poses[-1]
    x, y = calibration.observation_to_stage.apply((current.x_mm, current.y_mm))
    start = request.current.start
    if (
        hypot(x - start.x_mm, y - start.y_mm) > calibration.translation_error_mm
        or abs(
            (
                current.yaw_deg
                + calibration.observation_to_stage.yaw_deg
                - start.yaw_deg
                + 180
            )
            % 360
            - 180
        )
        > calibration.yaw_error_deg
    ):
        reasons.append("current_pose_mismatch")
    if reasons:
        return StageReceipt(
            status="HOLD", local_checks_passed=False, reasons=tuple(reasons)
        )
    return verify_stage(request)
