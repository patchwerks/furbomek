"""Closed replay contracts; timestamps use one explicitly identified local clock."""

from typing import Annotated, Literal

from pydantic import Field

from calibration_models import CalibrationInput, Contract, Finite, Frame, Positive

Digest = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
Identity = Annotated[str, Field(min_length=1, max_length=128)]
Milliseconds = Annotated[Finite, Field(ge=0, le=1e12)]
Bound = Annotated[Finite, Field(ge=0, le=1e6)]


class ClockAnchor(Contract):
    """Independently sampled PTS/local-monotonic pair, never wall time."""

    pts_ms: Milliseconds
    monotonic_ms: Milliseconds


class ClockMapping(Contract):
    """At least three pairs check drift/residual over the complete replay span."""

    clock_id: Identity
    anchors: Annotated[tuple[ClockAnchor, ...], Field(min_length=3)]
    measurement_uncertainty_ms: Positive
    maximum_uncertainty_ms: Annotated[Positive, Field(le=100)] = 25
    maximum_frame_delay_ms: Annotated[Positive, Field(le=600)] = 200


class GuardPhase(Contract):
    """Wire state stays independent from optical measurements and cutoff."""

    clock_id: Identity
    session_id: Identity
    command_id: Identity
    phase_id: Identity
    start_ms: Milliseconds
    stop_ms: Milliseconds
    observed_until_ms: Milliseconds
    timestamp_uncertainty_ms: Bound
    wire_status: Literal["completed", "held", "disarmed", "in_progress", "fault"]


class ExpectedMotion(Contract):
    """Predeclared body-relative displacement; zero axes constrain cross motion."""

    x_forward_mm: Finite
    y_left_mm: Finite
    yaw_ccw_deg: Finite
    height_up_mm: Finite
    translation_tolerance_mm: Positive = 3
    angular_tolerance_deg: Positive = 1
    settle_window_ms: Annotated[Positive, Field(ge=200)] = 200


class ScoringFrame(Contract):
    """Independent image identity plus phase/clock bindings and decoded geometry."""

    sequence: Annotated[int, Field(ge=0, strict=True)]
    pts_ms: Milliseconds
    received_monotonic_ms: Milliseconds
    session_id: Identity
    command_id: Identity
    phase_id: Identity
    content_sha256: Digest
    observation: Frame


class ScoreInput(Contract):
    """One isolated command phase; no camera or actuator access is implemented."""

    schema_version: Literal[1]
    calibration_id: Identity
    calibration: CalibrationInput
    calibration_valid_from_ms: Milliseconds
    calibration_valid_until_ms: Milliseconds
    marker_x_to_body_forward_deg: Finite
    clock: ClockMapping
    guard: GuardPhase
    expected: ExpectedMotion
    frames: Annotated[tuple[ScoringFrame, ...], Field(min_length=4)]


class Metric(Contract):
    """Measured scalar and conservative absolute error bound, not confidence."""

    value: Finite
    uncertainty: Bound
    unit: Literal["mm", "deg", "ms"]


class MotionMetrics(Contract):
    """Planar body motion, independent height posture, excursion and settling."""

    x_forward: Metric
    y_left: Metric
    yaw_ccw: Metric
    height_up: Metric
    peak_excursion: Metric
    post_stop_excursion: Metric
    settle_time: Metric | None


class ScoreResult(Contract):
    """Scored observation or unmeasurable outcome; neither grants authority."""

    schema_version: Literal[1] = 1
    outcome: Literal["motion", "partial", "unexpected", "no_travel", "unmeasurable"]
    motion_kind: Literal[
        "translation", "turn", "posture", "mixed", "stationary", "unmeasurable"
    ]
    reasons: tuple[str, ...] = ()
    physical_motion_authorized: Literal[False] = False
    provenance: Literal["synthetic", "measured", "unavailable"]
    recording_sha256: Digest | None = None
    calibration_id: str | None = None
    calibration_sha256: Digest | None = None
    camera_frame_sha256: tuple[Digest, ...] = ()
    guard: GuardPhase | None = None
    metrics: MotionMetrics | None = None
    timestamp_uncertainty_ms: Bound | None = None
    settled: bool | None = None
    slip_evidence: Literal["unmeasurable", "post_stop_drift"] = "unmeasurable"


class UncalibratedRecording(Contract):
    """Hash-bound private footage without manufactured calibration or Guard times."""

    schema_version: Literal[1]
    calibration: None
    provenance: Literal["measured"]
    recording_file: Annotated[str, Field(pattern=r"^[a-zA-Z0-9_-]+\.(mkv|png)$")]
    recording_sha256: Digest
