"""Offline calibrated replay scorer. Exit 2 holds; exit 0 never authorizes motion."""

import hashlib
from pathlib import Path
from typing import assert_never

from pydantic import ValidationError

from calibration_geometry import CalibrationHoldError
from calibration_images import detect_frame, import_images
from calibration_models import CalibrationInput, Frame, Pose
from calibration_solver import calibrate
from score_metrics import Observations, summarize
from score_models import ScoreInput, ScoreResult, ScoringFrame
from score_timing import project_timeline


def read_observation(frame: ScoringFrame, directory: Path) -> Frame:
    """Decode measured pixels and verify separate camera image content digest."""
    observation = frame.observation
    if observation.image_file is None:
        raise CalibrationHoldError("measured_image_provenance_missing")
    path = directory / observation.image_file
    if (
        path.is_symlink()
        or observation.image_sha256 != frame.content_sha256
        or hashlib.sha256(path.read_bytes()).hexdigest() != frame.content_sha256
    ):
        raise CalibrationHoldError("image_digest_mismatch")
    return detect_frame(path, observation)


def score_run(data: ScoreInput, directory: Path) -> ScoreResult:
    """Score one recorded phase, holding any invalid sample instead of skipping it."""
    calibration_digest = hashlib.sha256(
        data.calibration.model_dump_json().encode()
    ).hexdigest()
    try:
        timeline = project_timeline(data)
        calibration = import_images(data.calibration, directory)
        poses: list[Pose] = []
        position_errors: list[float] = []
        yaw_errors: list[float] = []
        for frame in data.frames:
            observation = frame.observation
            match calibration.provenance:
                case "measured":
                    observation = read_observation(frame, directory)
                case "synthetic":
                    if observation.image_file is not None:
                        observation = read_observation(frame, directory)
                case unreachable:
                    assert_never(unreachable)
            current = CalibrationInput.model_validate(
                calibration.model_dump() | {"current": observation.model_dump()}
            )
            receipt = calibrate(current, observation.captured_ms)
            match receipt.status:
                case "HOLD":
                    raise CalibrationHoldError(receipt.reasons[0])
                case "CALIBRATED_REPLAY" | "CALIBRATED_OBSERVATION":
                    pass
                case unreachable:
                    assert_never(unreachable)
            if receipt.translation_error_mm is None or receipt.yaw_error_deg is None:
                raise CalibrationHoldError("calibration_error_bound_missing")
            poses.append(receipt.recovered_poses[-1])
            position_errors.append(receipt.translation_error_mm)
            yaw_errors.append(receipt.yaw_error_deg)
        result = summarize(
            data,
            Observations(tuple(poses), max(position_errors), max(yaw_errors), timeline),
        )
    except CalibrationHoldError as error:
        result = ScoreResult(
            outcome="unmeasurable",
            motion_kind="unmeasurable",
            reasons=(error.reason,),
            provenance=data.calibration.provenance,
        )
    except (OSError, ValidationError) as error:
        result = ScoreResult(
            outcome="unmeasurable",
            motion_kind="unmeasurable",
            reasons=("invalid_replay_input", type(error).__name__),
            provenance=data.calibration.provenance,
        )
    return ScoreResult.model_validate(
        result.model_dump()
        | {
            "calibration_id": data.calibration_id,
            "calibration_sha256": calibration_digest,
            "camera_frame_sha256": tuple(f.content_sha256 for f in data.frames),
            "guard": data.guard.model_dump(),
        }
    )


if __name__ == "__main__":
    from score_cli import run_cli

    run_cli(score_run)
