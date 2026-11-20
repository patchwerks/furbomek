from pathlib import Path
from typing import Literal, assert_never

import pytest

from calibration_models import Frame, Pose
from score import score_run
from score_models import ExpectedMotion, ScoreInput, ScoringFrame
from tests.score_fixture import observed, replay


def movement(
    x: float = 0, y: float = 0, yaw: float = 0, height: float = 0
) -> ExpectedMotion:
    return ExpectedMotion(
        x_forward_mm=x, y_left_mm=y, yaw_ccw_deg=yaw, height_up_mm=height
    )


@pytest.mark.parametrize(
    ("target", "kind"),
    [
        (movement(x=20), "translation"),
        (movement(x=-20), "translation"),
        (movement(y=20), "translation"),
        (movement(y=-20), "translation"),
        (movement(yaw=20), "turn"),
        (movement(yaw=-20), "turn"),
        (movement(height=15), "posture"),
        (movement(x=20, yaw=20), "mixed"),
    ],
)
@pytest.mark.parametrize("view", [0, 1])
def test_observable_physical_transforms(
    tmp_path: Path, target: ExpectedMotion, kind: str, view: int
) -> None:
    data = replay(target, view=view, heading=25)
    result = score_run(data, tmp_path)
    assert result.outcome == "motion", result.reasons
    assert result.motion_kind == kind
    assert result.metrics is not None
    for metric, truth in zip(
        (
            result.metrics.x_forward,
            result.metrics.y_left,
            result.metrics.yaw_ccw,
            result.metrics.height_up,
        ),
        (
            target.x_forward_mm,
            target.y_left_mm,
            target.yaw_ccw_deg,
            target.height_up_mm,
        ),
        strict=True,
    ):
        assert abs(metric.value - truth) < metric.uncertainty
    assert result.settled is True


@pytest.mark.parametrize(
    ("actual", "outcome", "kind"),
    [
        (movement(), "no_travel", "stationary"),
        (movement(x=10), "partial", "translation"),
        (movement(x=-20), "unexpected", "translation"),
        (movement(y=20), "unexpected", "translation"),
        (movement(height=15), "unexpected", "posture"),
    ],
)
def test_observable_wire_ack_is_not_motion(
    tmp_path: Path, actual: ExpectedMotion, outcome: str, kind: str
) -> None:
    data = replay(movement(x=20), actual)
    result = score_run(data, tmp_path)
    assert result.outcome == outcome, result.reasons
    assert result.motion_kind == kind
    assert result.guard is not None
    assert result.guard.wire_status == "completed"


def replace_frame(data: ScoreInput, index: int, frame: ScoringFrame) -> ScoreInput:
    frames = list(data.frames)
    frames[index] = frame
    return ScoreInput.model_validate(data.model_dump() | {"frames": frames})


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ("tag_loss", "missing_or_duplicate_markers"),
        ("false_identity", "missing_or_duplicate_markers"),
        ("camera_bump", "fixed_reference_moved"),
        ("cropped", "boundary_feet_or_contact_unverified"),
        ("clipped", "cropped_marker"),
        ("repeated", "repeated_frame_content"),
        ("delay", "stale_or_future_frame"),
        ("phase", "mixed_guard_phase"),
        ("stale_reference", "camera_or_reference_revision_changed"),
        ("sequence", "lost_or_reordered_frame"),
    ],
)
def test_loss_holds_entire_phase(
    tmp_path: Path,
    change: Literal[
        "tag_loss",
        "false_identity",
        "camera_bump",
        "cropped",
        "clipped",
        "repeated",
        "delay",
        "phase",
        "stale_reference",
        "sequence",
    ],
    reason: str,
) -> None:
    data = replay(movement(x=20))
    raw = data.frames[4].model_dump()
    observation = data.frames[4].observation.model_dump()
    match change:
        case "tag_loss":
            observation["markers"] = data.frames[4].observation.markers[:4]
        case "false_identity":
            observation["markers"][-1]["marker_id"] = 11
        case "camera_bump":
            observation["markers"][0]["corners"] = [
                (x + 3, y) for x, y in data.frames[4].observation.markers[0].corners
            ]
        case "cropped":
            observation["boundary_visible"] = False
        case "clipped":
            observation["markers"][-1]["corners"] = [
                (1, y) for _, y in data.frames[4].observation.markers[-1].corners
            ]
        case "repeated":
            raw["content_sha256"] = data.frames[3].content_sha256
        case "delay":
            raw["received_monotonic_ms"] += 700
        case "phase":
            raw["phase_id"] = "other-phase"
        case "stale_reference":
            observation["reference_revision"] = "old-reference"
        case "sequence":
            raw["sequence"] = 999
        case unreachable:
            assert_never(unreachable)
    raw["observation"] = Frame.model_validate(observation)
    result = score_run(
        replace_frame(data, 4, ScoringFrame.model_validate(raw)), tmp_path
    )
    assert result.outcome == "unmeasurable"
    assert result.reasons == (reason,)
    assert result.metrics is None


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ("clock", "timestamp_uncertainty_exceeds_bound"),
        ("small_move", "metric_uncertainty_exceeds_bound"),
        ("stale", "phase_or_calibration_interval_invalid"),
        ("no_tail", "phase_coverage_incomplete"),
    ],
)
def test_uncertainty_holds(
    tmp_path: Path,
    change: Literal["clock", "small_move", "stale", "no_tail"],
    reason: str,
) -> None:
    data = replay(movement(x=20))
    raw = data.model_dump()
    match change:
        case "clock":
            raw["clock"]["anchors"][1]["monotonic_ms"] += 50
        case "small_move":
            raw["expected"]["x_forward_mm"] = 3
        case "stale":
            raw["calibration_valid_until_ms"] = 10500
        case "no_tail":
            raw["frames"] = data.frames[:-4]
        case unreachable:
            assert_never(unreachable)
    result = score_run(ScoreInput.model_validate(raw), tmp_path)
    assert result.outcome == "unmeasurable"
    assert result.reasons == (reason,)


@pytest.mark.parametrize("wire_status", ["held", "disarmed", "in_progress", "fault"])
def test_observable_nonfinal_no_motion(tmp_path: Path, wire_status: str) -> None:
    data = replay(movement(x=20), movement())
    raw = data.model_dump()
    raw["guard"]["wire_status"] = wire_status
    result = score_run(ScoreInput.model_validate(raw), tmp_path)
    assert result.outcome == "no_travel"
    assert result.guard is not None
    assert result.guard.wire_status == wire_status


def test_observable_post_stop_drift_is_unsettled(tmp_path: Path) -> None:
    data = replay(movement(x=20))
    frames = list(data.frames)
    for i in range(7, 16):
        observation = observed(
            Pose(x_mm=75 + (i - 6) * 2, y_mm=55, z_mm=-65, yaw_deg=0)
        )
        frames[i] = ScoringFrame.model_validate(
            frames[i].model_dump() | {"observation": observation}
        )
    result = score_run(
        ScoreInput.model_validate(data.model_dump() | {"frames": frames}), tmp_path
    )
    assert result.outcome == "partial"
    assert result.reasons == ("unsettled",)
    assert result.slip_evidence == "post_stop_drift"
    assert result.metrics is not None
    assert result.metrics.settle_time is None
    assert result.metrics.post_stop_excursion.value == pytest.approx(18, abs=0.1)


def test_observable_surveyed_mount_offset(tmp_path: Path) -> None:
    data = replay(movement(x=20))
    frames = [
        ScoringFrame.model_validate(
            frame.model_dump()
            | {
                "observation": observed(
                    Pose(x_mm=55 + 20 * min(i / 6, 1), y_mm=55, z_mm=-65, yaw_deg=-90)
                )
            }
        )
        for i, frame in enumerate(data.frames)
    ]
    data = ScoreInput.model_validate(
        data.model_dump() | {"frames": frames, "marker_x_to_body_forward_deg": 90}
    )
    result = score_run(data, tmp_path)
    assert result.outcome == "motion", result.reasons
    assert result.metrics is not None
    assert result.metrics.x_forward.value == pytest.approx(20, abs=0.1)
    assert result.metrics.y_left.value == pytest.approx(0, abs=0.1)


def test_observable_peak_keeps_midphase_excursion(tmp_path: Path) -> None:
    data = replay(movement(x=20))
    observation = observed(Pose(x_mm=85, y_mm=55, z_mm=-65, yaw_deg=0))
    frame = ScoringFrame.model_validate(
        data.frames[3].model_dump() | {"observation": observation}
    )
    result = score_run(replace_frame(data, 3, frame), tmp_path)
    assert result.metrics is not None
    assert result.metrics.peak_excursion.value == pytest.approx(30, abs=0.1)
    assert result.metrics.x_forward.value == pytest.approx(20, abs=0.1)
