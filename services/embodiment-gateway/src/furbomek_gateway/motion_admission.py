"""Pure stage-evidence eligibility; never an actuator authorization path."""

from typing import Annotated, Literal

from pydantic import Field

from furbomek_gateway.motion_contracts import (
    MotionProfile,
    ObservationCalibration,
    StageProfile,
)
from furbomek_gateway.motion_geometry import Contract, Identifier


class AdmissionContext(Contract):
    """Explicit current view and clock alongside the immutable evidence records."""

    profile: MotionProfile
    stage: StageProfile
    calibration: ObservationCalibration
    observation_revision: Identifier
    now_ms: Annotated[int, Field(ge=0, strict=True)]


class StageAdmission(Contract):
    """Eligibility receipt whose holds must survive serialization."""

    decision: Literal["eligible", "hold"]
    hold_reasons: tuple[str, ...]
    profile_id: Identifier
    stage_id: Identifier
    calibration_id: Identifier
    physical_motion_authorized: Literal[False] = False


def assess_stage(context: AdmissionContext) -> StageAdmission:
    """Refuse inconsistent, stale, cropped or incompatible stage evidence."""
    p, s, c = context.profile, context.stage, context.calibration
    checks = (
        (s.profile_id == p.profile_id, "profile_changed"),
        (
            s.robot_revision == p.robot_revision
            and s.installed_sha256 == p.installed_sha256,
            "robot_changed",
        ),
        (
            s.calibration_id == c.calibration_id
            and s.stage_id == c.stage_id
            and s.stage_frame_id == c.stage_frame_id,
            "calibration_binding_mismatch",
        ),
        (context.observation_revision == c.observation_revision, "observation_changed"),
        (c.valid_from_ms <= context.now_ms < c.valid_until_ms, "calibration_expired"),
        (
            all(c.coverage.contains(v) for v in s.usable_polygon.vertices),
            "coverage_incomplete",
        ),
        (p.surface.covers(s.surface), "surface_outside_tested_range"),
        (
            p.start_pose in c.observable_poses and p.end_pose in c.observable_poses,
            "posture_unobservable",
        ),
        (not s.hazards, "unresolved_hazards"),
    )
    reasons = tuple(reason for passed, reason in checks if not passed)
    return StageAdmission(
        decision="hold" if reasons else "eligible",
        hold_reasons=reasons,
        profile_id=p.profile_id,
        stage_id=s.stage_id,
        calibration_id=c.calibration_id,
    )
