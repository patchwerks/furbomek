"""Body-relative displacement and bounded optical outcome classification."""

import math
from dataclasses import dataclass
from itertools import pairwise
from typing import Literal

import numpy as np

from calibration_geometry import CalibrationHoldError
from calibration_models import Pose
from score_models import Metric, MotionMetrics, ScoreInput, ScoreResult
from score_timing import Timeline


@dataclass(frozen=True, slots=True)
class Observations:
    """Recovered marker poses and independent absolute calibration errors."""

    poses: tuple[Pose, ...]
    position_error_mm: float
    yaw_error_deg: float
    timeline: Timeline


def summarize(data: ScoreInput, observations: Observations) -> ScoreResult:
    """Classify geometry independently of the Guard's wire-status assertion."""
    poses, times = observations.poses, observations.timeline.times
    first = poses[0]
    angle = math.radians(first.yaw_deg + data.marker_x_to_body_forward_deg)
    values = np.array(
        [
            [
                (p.x_mm - first.x_mm) * math.cos(angle)
                + (p.y_mm - first.y_mm) * math.sin(angle),
                (p.x_mm - first.x_mm) * math.sin(angle)
                - (p.y_mm - first.y_mm) * math.cos(angle),
                -((p.yaw_deg - first.yaw_deg + 180) % 360 - 180),
                first.z_mm - p.z_mm,
            ]
            for p in poses
        ]
    )
    velocities = np.abs(np.diff(values, axis=0) / np.diff(times)[:, None])
    timing = observations.timeline.uncertainty_ms
    peak = float(np.linalg.norm(values[:, :2], axis=1).max())
    spatial = 2 * observations.position_error_mm + peak * math.sin(
        math.radians(observations.yaw_error_deg)
    )
    bounds = (
        np.array(
            [
                spatial,
                spatial,
                2 * observations.yaw_error_deg,
                2 * observations.position_error_mm,
            ]
        )
        + velocities.max(axis=0) * timing * 2
    )
    expected = data.expected
    targets = np.array(
        [
            expected.x_forward_mm,
            expected.y_left_mm,
            expected.yaw_ccw_deg,
            expected.height_up_mm,
        ]
    )
    if (
        float(bounds[[0, 1, 3]].max()) > 5
        or bounds[2] > 2
        or any(
            abs(target) > 0 and bound * 4 >= abs(target)
            for target, bound in zip(targets, bounds, strict=True)
        )
    ):
        raise CalibrationHoldError("metric_uncertainty_exceeds_bound")
    stop_index = max(i for i, time in enumerate(times) if time <= data.guard.stop_ms)
    after_stop = values[stop_index:] - values[stop_index]
    post_stop = float(np.linalg.norm(after_stop[:, :2], axis=1).max())
    settle = next(
        (
            i
            for i, time in enumerate(times)
            if time - timing >= data.guard.stop_ms
            and times[-1] - time - 2 * timing >= expected.settle_window_ms
            and bool(np.all(np.abs(values[i:] - values[i]) <= bounds))
        ),
        None,
    )
    settle_time = (
        None
        if settle is None
        else Metric(
            value=max(0, times[settle] - data.guard.stop_ms),
            uncertainty=timing * 2 + max(b - a for a, b in pairwise(times)),
            unit="ms",
        )
    )
    moving = np.max(np.abs(values), axis=0) > bounds
    planar, turning, posture = (
        bool(np.any(moving[:2])),
        bool(moving[2]),
        bool(moving[3]),
    )
    kind: Literal["translation", "turn", "posture", "mixed", "stationary"] = (
        "stationary"
    )
    if sum((planar, turning, posture)) > 1:
        kind = "mixed"
    elif planar:
        kind = "translation"
    elif turning:
        kind = "turn"
    elif posture:
        kind = "posture"
    tolerances = np.array(
        [
            expected.translation_tolerance_mm,
            expected.translation_tolerance_mm,
            expected.angular_tolerance_deg,
            expected.translation_tolerance_mm,
        ]
    )
    wrong = any(
        bool(np.any(values[:, i] * np.sign(target) < -bounds[i]))
        if target != 0
        else bool(moving[i])
        for i, target in enumerate(targets)
    )
    outcome: Literal["motion", "partial", "unexpected", "no_travel"] = "motion"
    reasons: tuple[str, ...] = ()
    if not bool(np.any(moving)):
        outcome = "no_travel"
    elif wrong:
        outcome = "unexpected"
    elif (
        bool(np.any(np.abs(values[-1] - targets) > bounds + tolerances))
        or settle is None
    ):
        outcome = "partial"
    if settle is None:
        reasons = ("unsettled",)
    metrics = MotionMetrics(
        x_forward=Metric(
            value=float(values[-1, 0]), uncertainty=float(bounds[0]), unit="mm"
        ),
        y_left=Metric(
            value=float(values[-1, 1]), uncertainty=float(bounds[1]), unit="mm"
        ),
        yaw_ccw=Metric(
            value=float(values[-1, 2]), uncertainty=float(bounds[2]), unit="deg"
        ),
        height_up=Metric(
            value=float(values[-1, 3]), uncertainty=float(bounds[3]), unit="mm"
        ),
        peak_excursion=Metric(
            value=peak, uncertainty=float(np.linalg.norm(bounds[:2])), unit="mm"
        ),
        post_stop_excursion=Metric(
            value=post_stop, uncertainty=float(np.linalg.norm(bounds[:2])), unit="mm"
        ),
        settle_time=settle_time,
    )
    return ScoreResult(
        outcome=outcome,
        motion_kind=kind,
        reasons=reasons,
        provenance=data.calibration.provenance,
        metrics=metrics,
        timestamp_uncertainty_ms=timing,
        settled=settle is not None,
        slip_evidence="post_stop_drift"
        if post_stop > float(np.linalg.norm(bounds[:2]))
        else "unmeasurable",
    )
