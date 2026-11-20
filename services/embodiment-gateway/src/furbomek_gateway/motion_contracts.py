"""Versioned portable measurements, observation provenance and stage surveys."""

import hashlib
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from furbomek_gateway.guard_models import ActionName
from furbomek_gateway.motion_geometry import (
    Contract,
    Digest,
    Identifier,
    MotionContractError,
    Nonnegative,
    Polygon,
    Positive,
    SurfaceClass,
    Transform,
)


class TrialEvidence(Contract):
    """Historical collection provenance; never rewritten on stage transfer."""

    schema_version: Literal[1]
    trial_id: Identifier
    calibration_id: Identifier
    artifact_sha256: Digest
    provenance: Literal["synthetic", "recorded_replay", "measured"]
    sample_count: Annotated[int, Field(gt=0, strict=True)]


class MotionProfile(Contract):
    """Robot-relative envelope identity independent of site and camera."""

    schema_version: Literal[1]
    units: Literal["mm_deg"] = "mm_deg"
    body_frame: Literal["x_forward_y_left_yaw_ccw"] = "x_forward_y_left_yaw_ccw"
    robot_revision: Identifier
    installed_sha256: Digest
    gait_revision: Identifier
    action: ActionName
    start_pose: Identifier
    end_pose: Identifier
    power_regime: Identifier
    load_class: Identifier
    surface: SurfaceClass
    delta: Transform
    swept_radius_mm: Positive
    stopping_distance_mm: Nonnegative
    interval_travel_mm: Nonnegative
    uncertainty_mm: Nonnegative
    sample_count: Annotated[int, Field(gt=0, strict=True)]
    assumptions: Annotated[tuple[Identifier, ...], Field(min_length=1)]
    evidence: Annotated[tuple[TrialEvidence, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def direction(self) -> Self:
        """Reject nominal movement whose observed primary axis has wrong sign."""
        signed = {
            "forward": self.delta.x_mm,
            "backward": -self.delta.x_mm,
            "left": self.delta.y_mm,
            "right": -self.delta.y_mm,
            "turn_left": self.delta.yaw_deg,
            "turn_right": -self.delta.yaw_deg,
            "active": 1.0,
            "sleep": 1.0,
        }
        if signed[self.action] <= 0:
            msg = "unexpected_motion_direction"
            raise MotionContractError(msg)
        return self

    @property
    def profile_id(self) -> str:
        """Hash the versioned body model, excluding historical collection location."""
        payload = self.model_dump_json(exclude={"evidence"})
        return "motion-v1-" + hashlib.sha256(payload.encode()).hexdigest()

    @property
    def clearance_mm(self) -> float:
        """Conservative radial clearance; task 9 places this on the surveyed stage."""
        return (
            self.swept_radius_mm
            + self.stopping_distance_mm
            + self.interval_travel_mm
            + self.uncertainty_mm
        )


class ObservationCalibration(Contract):
    """Private calibrated observation tied to one stage and view revision."""

    schema_version: Literal[1]
    units: Literal["mm_deg"] = "mm_deg"
    calibration_id: Identifier
    stage_id: Identifier
    stage_frame_id: Identifier
    observation_revision: Identifier
    observation_to_stage: Transform
    coverage: Polygon
    valid_from_ms: Annotated[int, Field(ge=0, strict=True)]
    valid_until_ms: Annotated[int, Field(gt=0, strict=True)]
    translation_error_mm: Annotated[Nonnegative, Field(le=5)]
    yaw_error_deg: Annotated[Nonnegative, Field(le=2)]
    minimum_translation_mm: Positive
    minimum_yaw_deg: Positive
    independent_validation_sha256: Digest
    observable_poses: Annotated[tuple[Identifier, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def scoring_limits(self) -> Self:
        """Require independent error below one quarter of the minimum scored move."""
        if (
            self.valid_until_ms <= self.valid_from_ms
            or self.translation_error_mm * 4 >= self.minimum_translation_mm
            or self.yaw_error_deg * 4 >= self.minimum_yaw_deg
        ):
            msg = "calibration_scoring_limits"
            raise MotionContractError(msg)
        return self


class StageProfile(Contract):
    """Surveyed site with explicit evidence; no default geometry or admission."""

    schema_version: Literal[1]
    units: Literal["mm_deg"] = "mm_deg"
    stage_id: Identifier
    stage_frame_id: Identifier
    calibration_id: Identifier
    profile_id: Identifier
    robot_revision: Identifier
    installed_sha256: Digest
    surface: SurfaceClass
    usable_polygon: Polygon
    containment_evidence_sha256: Digest
    hazards: tuple[Identifier, ...]
    survey_sha256: Digest
