"""Independent Brown camera projection of dimensioned physical fixture poses."""

import hashlib
import math
from pathlib import Path

import numpy as np

from calibration_models import CalibrationInput, Frame, Marker, Pose, ValidationPose
from score_models import (
    ClockAnchor,
    ClockMapping,
    ExpectedMotion,
    GuardPhase,
    ScoreInput,
    ScoringFrame,
)
from tests.fixture_scene import rotation, scene


def observed(pose: Pose, view: int = 0) -> Frame:
    """Project target corners from known physical pose, without scorer geometry."""
    baseline = scene(view).reference
    corners = np.array([[-20, -20, 0], [20, -20, 0], [20, 20, 0], [-20, 20, 0]])
    world = corners @ rotation((0, 0, pose.yaw_deg)).T + [
        pose.x_mm,
        pose.y_mm,
        pose.z_mm,
    ]
    camera = world @ rotation((12, -18, 5) if view == 0 else (-8, 8, -12)).T + [
        -60,
        -60,
        600 if view == 0 else 640,
    ]
    xy = camera[:, :2] / camera[:, 2:]
    x, y = xy[:, 0], xy[:, 1]
    radius = x * x + y * y
    radial = 1 - 0.18 * radius + 0.04 * radius**2 - 0.006 * radius**3
    u = 580 * (x * radial + 0.002 * x * y - 0.001 * (radius + 2 * x * x)) + 318
    v = 575 * (y * radial + 0.001 * (radius + 2 * y * y) - 0.002 * x * y) + 241
    marker = Marker.model_validate(
        {"marker_id": 10, "corners": np.column_stack((u, v)).tolist()}
    )
    return Frame.model_validate(
        baseline.model_dump() | {"markers": [*baseline.markers[:4], marker]}
    )


def replay(
    expected: ExpectedMotion,
    actual: ExpectedMotion | None = None,
    *,
    view: int = 0,
    heading: float = 0,
) -> ScoreInput:
    """Dimensioned fixture moves in true body forward/left, with 15 fps capture."""
    truth = expected if actual is None else actual
    calibration = scene(view)
    survey = tuple(
        Pose(x_mm=x, y_mm=y, z_mm=z, yaw_deg=yaw)
        for x, y, z, yaw in (
            (20, 20, -40, -30),
            (100, 20, -40, 30),
            (100, 100, -90, 30),
            (20, 100, -90, -30),
        )
    )
    start = Pose(x_mm=55, y_mm=55, z_mm=-65, yaw_deg=-heading)
    calibration = CalibrationInput.model_validate(
        calibration.model_dump()
        | {
            "validations": [
                ValidationPose(frame=observed(p, view), expected=p) for p in survey
            ],
            "current": observed(start, view),
        }
    )
    frames: list[ScoringFrame] = []
    theta = math.radians(heading)
    for i in range(16):
        fraction = min(i / 6, 1)
        pose = Pose(
            x_mm=55
            + fraction
            * (
                truth.x_forward_mm * math.cos(theta) - truth.y_left_mm * math.sin(theta)
            ),
            y_mm=55
            - fraction
            * (
                truth.x_forward_mm * math.sin(theta) + truth.y_left_mm * math.cos(theta)
            ),
            z_mm=-65 - fraction * truth.height_up_mm,
            yaw_deg=-heading - fraction * truth.yaw_ccw_deg,
        )
        observation = observed(pose, view)
        frames.append(
            ScoringFrame(
                sequence=i,
                pts_ms=i * 1000 / 15,
                received_monotonic_ms=10010 + i * 1000 / 15,
                session_id="fixture-session",
                command_id="fixture-command",
                phase_id="fixture-phase",
                content_sha256=hashlib.sha256(
                    f"synthetic-frame-{i}-{observation.model_dump_json()}".encode()
                ).hexdigest(),
                observation=observation,
            )
        )
    return ScoreInput(
        schema_version=1,
        calibration_id=f"synthetic-camera-{view}",
        calibration=calibration,
        calibration_valid_from_ms=9000,
        calibration_valid_until_ms=12000,
        marker_x_to_body_forward_deg=0,
        clock=ClockMapping(
            clock_id="fixture-clock",
            measurement_uncertainty_ms=0.2,
            anchors=tuple(
                ClockAnchor(pts_ms=t, monotonic_ms=10000 + t) for t in (0, 500, 1000)
            ),
        ),
        guard=GuardPhase(
            clock_id="fixture-clock",
            session_id="fixture-session",
            command_id="fixture-command",
            phase_id="fixture-phase",
            start_ms=10020,
            stop_ms=10450,
            observed_until_ms=10980,
            timestamp_uncertainty_ms=0.2,
            wire_status="completed",
        ),
        expected=expected,
        frames=tuple(frames),
    )


def write_replay(path: Path, data: ScoreInput) -> None:
    """Persist a replay for direct CLI consumers, with no live resources."""
    _ = path.write_text(data.model_dump_json(indent=2))
