"""Private stage evidence DTOs; none represents an authenticated release permit."""

import hashlib
from typing import Annotated, Literal

from pydantic import Field

from furbomek_gateway.motion_admission import AdmissionContext
from furbomek_gateway.motion_geometry import (
    Contract,
    Digest,
    Identifier,
    Nonnegative,
    Polygon,
    Positive,
    SurfaceClass,
    Transform,
)


class StageSurvey(Contract):
    """Independent survey and containment records, bound by content digests."""

    stage_id: Identifier
    revision: Identifier
    stage_frame_id: Identifier
    usable_polygon: Polygon
    surface: SurfaceClass
    obstacles: tuple[Polygon, ...]
    source_sha256: Digest

    @property
    def digest(self) -> str:
        """Bind geometry, revision, and source without granting it authority."""
        return hashlib.sha256(self.model_dump_json().encode()).hexdigest()


class ContainmentCheck(Contract):
    """Independent containment survey in the same anchored metric frame."""

    stage_id: Identifier
    survey_sha256: Digest
    contained_polygon: Polygon
    source_sha256: Digest

    @property
    def digest(self) -> str:
        """Bind the checked region to the exact survey."""
        return hashlib.sha256(self.model_dump_json().encode()).hexdigest()


class CurrentConditions(Contract):
    """Fresh caller observations; must match the particular motion profile."""

    robot_revision: Identifier
    installed_sha256: Digest
    gait_revision: Identifier
    power_regime: Identifier
    load_class: Identifier
    surface: SurfaceClass
    pose: Identifier
    footprint_radius_mm: Positive
    start: Transform
    observed_ms: Annotated[int, Field(ge=0, strict=True)]
    maximum_age_ms: Annotated[int, Field(gt=0, le=600, strict=True)]
    survey_revision: Identifier


class StageRequest(Contract):
    """One bounded step against private stage evidence, never an execution request."""

    schema_version: Literal[1]
    mode: Literal["replay_comparison", "observation_check"]
    comparison_id: Identifier | None = None
    context: AdmissionContext
    survey: StageSurvey
    containment: ContainmentCheck
    current: CurrentConditions
    approved_profile_ids: Annotated[tuple[Identifier, ...], Field(min_length=1)]
    invalidated: bool
    clearance_margin_mm: Nonnegative


class StageReceipt(Contract):
    """Local eligibility and physical release status remain separate."""

    schema_version: Literal[1] = 1
    status: Literal["REPLAY_ELIGIBLE", "HOLD"]
    local_checks_passed: bool
    reasons: tuple[str, ...]
    request_sha256: Digest | None = None
    profile_id: Identifier | None = None
    stage_id: Identifier | None = None
    required_clearance_mm: Nonnegative | None = None
    physical_motion_authorized: Literal[False] = False
    supervised_status: Literal["HOLD"] = "HOLD"
    unattended_status: Literal["HOLD"] = "HOLD"
