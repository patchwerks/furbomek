"""Closed offline trial inputs and evidence receipts; no dispatch capability."""

from typing import Annotated, Literal

from pydantic import Field

from calibration_models import Contract, Finite, Positive
from score_models import Bound, Digest, Identity, ScoreInput, ScoreResult
from trials_gateway import ActionName, MotionProfile, StageProfile, SurfaceClass


class ProfileConditions(Contract):
    """Portable identity and predeclared bounds, independent of the stage."""

    action: ActionName
    start_pose: Identity
    end_pose: Identity
    robot_revision: Identity
    installed_sha256: Digest
    gait_revision: Identity
    power_regime: Identity
    load_class: Identity
    surface: SurfaceClass
    voltage_bands: Annotated[tuple[tuple[Positive, Positive], ...], Field(min_length=1)]
    limited_voltage_evidence: Digest | None = None
    swept_radius_mm: Positive
    interval_travel_mm: Bound


class Trial(Contract):
    """One attempt, including rejected or unscorable observations."""

    trial_id: Identity
    conditions: ProfileConditions
    stage: StageProfile
    stage_start_mm: tuple[Finite, Finite]
    independent_clearance_sha256: Digest
    independent_cutoff_sha256: Digest
    observed_surface: SurfaceClass
    observed_voltage: Positive
    start_pose: Identity
    end_pose: Identity
    normal_disarm: bool
    score: ScoreInput | None


class TrialManifest(Contract):
    """Replay payload; measurement provenance remains in each optical input."""

    schema_version: Literal[1]
    profiles: Annotated[tuple[ProfileConditions, ...], Field(min_length=1)]
    trials: tuple[Trial, ...]


class TrialOutcome(Contract):
    """Full denominator with machine scoring and independent protocol status."""

    trial_id: Identity
    accepted: bool
    reasons: tuple[str, ...]
    evidence_sha256: Digest
    score: ScoreResult | None
    initial_heading_deg: Finite | None = None


class ProfileOutcome(Contract):
    """Portable candidate plus separately retained collection evidence."""

    conditions: ProfileConditions
    status: Literal["HOLD", "REPLAY_COMPLETE"]
    reasons: tuple[str, ...]
    total_attempts: int
    valid_trials: int
    candidate: MotionProfile | None = None
    profile_id: str | None = None


class CatalogReceipt(Contract):
    """Replay completeness is never supervised or unattended qualification."""

    schema_version: Literal[1] = 1
    status: Literal["HOLD", "REPLAY_COMPLETE"]
    reasons: tuple[str, ...] = ()
    physical_motion_authorized: Literal[False] = False
    supervised_status: Literal["HOLD"] = "HOLD"
    unattended_status: Literal["HOLD"] = "HOLD"
    profiles: tuple[ProfileOutcome, ...] = ()
    trials: tuple[TrialOutcome, ...] = ()
