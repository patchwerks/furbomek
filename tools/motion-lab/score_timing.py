"""Validate PTS projection without treating receipt time as capture time."""

from dataclasses import dataclass
from itertools import pairwise

from calibration_geometry import CalibrationHoldError
from score_models import ScoreInput


@dataclass(frozen=True, slots=True)
class Timeline:
    """Validated capture projections with conservative timestamp bounds."""

    times: tuple[float, ...]
    uncertainty_ms: float


# Named rejection gates retain distinct audit reasons.
def project_timeline(data: ScoreInput) -> Timeline:  # noqa: PLR0912
    """Reject extrapolation, mixed phases, replay, clock drift and receipt lag."""
    clock, guard = data.clock, data.guard
    anchors = clock.anchors
    if clock.clock_id != guard.clock_id:
        raise CalibrationHoldError("clock_identity_mismatch")
    if any(
        b.pts_ms <= a.pts_ms or b.monotonic_ms <= a.monotonic_ms
        for a, b in pairwise(anchors)
    ):
        raise CalibrationHoldError("clock_anchors_not_ordered")
    scale = (anchors[-1].monotonic_ms - anchors[0].monotonic_ms) / (
        anchors[-1].pts_ms - anchors[0].pts_ms
    )
    if abs(scale - 1) > 0.001:
        raise CalibrationHoldError("clock_drift_exceeds_bound")
    offset = anchors[0].monotonic_ms - scale * anchors[0].pts_ms
    residual = max(abs(a.monotonic_ms - (a.pts_ms * scale + offset)) for a in anchors)
    uncertainty = (
        residual + clock.measurement_uncertainty_ms + guard.timestamp_uncertainty_ms
    )
    if uncertainty > clock.maximum_uncertainty_ms:
        raise CalibrationHoldError("timestamp_uncertainty_exceeds_bound")
    if not (
        data.calibration_valid_from_ms
        <= guard.start_ms
        < guard.stop_ms
        < guard.observed_until_ms
        < data.calibration_valid_until_ms
    ):
        raise CalibrationHoldError("phase_or_calibration_interval_invalid")
    if len({f.content_sha256 for f in data.frames}) != len(data.frames):
        raise CalibrationHoldError("repeated_frame_content")
    if any(
        b.sequence != a.sequence + 1 or b.pts_ms <= a.pts_ms
        for a, b in pairwise(data.frames)
    ):
        raise CalibrationHoldError("lost_or_reordered_frame")
    times = tuple(f.pts_ms * scale + offset for f in data.frames)
    for frame, capture in zip(data.frames, times, strict=True):
        if (frame.session_id, frame.command_id, frame.phase_id) != (
            guard.session_id,
            guard.command_id,
            guard.phase_id,
        ):
            raise CalibrationHoldError("mixed_guard_phase")
        if not anchors[0].pts_ms <= frame.pts_ms <= anchors[-1].pts_ms:
            raise CalibrationHoldError("clock_projection_extrapolation")
        if (
            not -uncertainty
            <= frame.received_monotonic_ms - capture
            <= clock.maximum_frame_delay_ms
        ):
            raise CalibrationHoldError("stale_or_future_frame")
        if (
            not data.calibration_valid_from_ms
            <= capture - uncertainty
            < capture + uncertainty
            < data.calibration_valid_until_ms
        ):
            raise CalibrationHoldError("stale_calibration")
    if any(b - a > 150 for a, b in pairwise(times)):
        raise CalibrationHoldError("observation_gap")
    if not (
        times[0] + uncertainty <= guard.start_ms
        and times[1] - uncertainty >= guard.start_ms
        and times[-1] - uncertainty >= guard.observed_until_ms
        and times[-1] - guard.observed_until_ms <= 150
    ):
        raise CalibrationHoldError("phase_coverage_incomplete")
    return Timeline(times, uncertainty)
