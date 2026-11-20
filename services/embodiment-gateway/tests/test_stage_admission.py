"""Per-step geometry, exact evidence binding and physical authority regressions."""

import json
from pathlib import Path
from typing import Literal, assert_never

import pytest
from pydantic import ValidationError

from furbomek_gateway.stage_admission import verify_stage
from furbomek_gateway.stage_models import StageRequest

type FixtureValue = (
    str
    | float
    | bool
    | list[str]
    | list[float]
    | tuple[FixtureValue, ...]
    | dict[str, FixtureValue]
    | None
)


def request(view: int = 0) -> StageRequest:
    path = (
        Path(__file__).resolve().parents[3]
        / "tools/motion-lab/fixtures"
        / f"stage-{view}.json"
    )
    return StageRequest.model_validate(json.loads(path.read_bytes())["request"])


def test_two_independent_stages_select_identical_body_profile() -> None:
    first, second = request(), request(1)
    assert first.context.profile.profile_id == second.context.profile.profile_id
    assert first.context.stage.stage_id != second.context.stage.stage_id
    assert (
        first.context.calibration.observation_to_stage
        != second.context.calibration.observation_to_stage
    )
    assert first.survey.digest != second.survey.digest
    for data in (first, second):
        receipt = verify_stage(data)
        assert receipt.status == "REPLAY_ELIGIBLE", receipt.reasons
        assert receipt.local_checks_passed
        assert receipt.physical_motion_authorized is False


@pytest.mark.parametrize(
    ("path", "value", "reason"),
    [
        (("invalidated",), True, "stage_invalidated"),
        (("comparison_id",), None, "named_replay_comparison_required"),
        (("approved_profile_ids",), ["unselected"], "profile_not_selected"),
        (("context", "observation_revision"), "camera-moved", "observation_changed"),
        (("context", "now_ms"), 10600, "calibration_expired"),
        (
            ("context", "stage", "surface", "static_traction"),
            [0.1, 0.2],
            "surface_outside_tested_range",
        ),
        (
            ("context", "stage", "hazards"),
            ["unresolved-obstacle"],
            "unresolved_hazards",
        ),
        (("current", "survey_revision"), "moved-arena", "survey_changed"),
        (("context", "profile", "gait_revision"), "profile-revised", "profile_changed"),
        (
            ("current", "surface", "static_traction"),
            [0.1, 0.2],
            "current_surface_changed",
        ),
        (("current", "gait_revision"), "changed-gait", "current_robot_changed"),
        (("current", "pose"), "wrong-posture", "current_profile_conditions_changed"),
        (
            ("current", "power_regime"),
            "changed-power",
            "current_profile_conditions_changed",
        ),
        (
            ("current", "load_class"),
            "changed-load",
            "current_profile_conditions_changed",
        ),
        (("current", "footprint_radius_mm"), 100.0, "footprint_outside_profile"),
        (("current", "observed_ms"), 999, "current_observation_stale"),
        (("current", "start", "x_mm"), -50.0, "step_boundary_clearance"),
        (("containment", "source_sha256"), "0" * 64, "containment_binding_mismatch"),
        (("survey", "source_sha256"), "0" * 64, "survey_changed"),
    ],
)
def test_changed_evidence_holds_selected_step(
    path: tuple[str, ...],
    value: str | float | bool | list[str] | list[float] | None,
    reason: str,
) -> None:
    raw: dict[str, FixtureValue] = request().model_dump()
    cursor = raw
    for key in path[:-1]:
        child = cursor[key]
        assert isinstance(child, dict)
        cursor = child
    cursor[path[-1]] = value
    result = verify_stage(StageRequest.model_validate(raw))
    assert result.status == "HOLD"
    assert reason in result.reasons


@pytest.mark.parametrize("part", ["containment", "survey", "current", "context"])
def test_missing_evidence_is_not_defaulted(part: str) -> None:
    raw = request().model_dump()
    del raw[part]
    with pytest.raises(ValidationError):
        _ = StageRequest.model_validate(raw)


@pytest.mark.parametrize("kind", ["cropped", "uncertain", "obstacle", "containment"])
def test_geometry_is_rechecked_after_content_rebinding(
    kind: Literal["cropped", "uncertain", "obstacle", "containment"],
) -> None:
    raw = request().model_dump()
    polygon = {"vertices": [[50.0, 50.0], [70.0, 50.0], [70.0, 70.0], [50.0, 70.0]]}
    reasons = {
        "cropped": "coverage_incomplete",
        "uncertain": "invalid",
        "obstacle": "step_obstacle_clearance",
        "containment": "containment_incomplete",
    }
    match kind:
        case "cropped":
            raw["context"]["calibration"]["coverage"] = polygon
        case "uncertain":
            raw["context"]["calibration"]["translation_error_mm"] = 6.0
            with pytest.raises(ValidationError):
                _ = StageRequest.model_validate(raw)
            return
        case "obstacle":
            raw["survey"]["obstacles"] = [polygon]
        case "containment":
            raw["containment"]["contained_polygon"] = polygon
        case _:
            assert_never(kind)
    data = StageRequest.model_validate(raw)
    raw["containment"]["survey_sha256"] = data.survey.digest
    raw["context"]["stage"]["survey_sha256"] = data.survey.digest
    data = StageRequest.model_validate(raw)
    raw["context"]["stage"]["containment_evidence_sha256"] = data.containment.digest
    result = verify_stage(StageRequest.model_validate(raw))
    assert result.status == "HOLD"
    assert reasons[kind] in result.reasons


def test_observation_checks_cannot_mint_physical_authority() -> None:
    raw = request().model_dump() | {"mode": "observation_check", "comparison_id": None}
    result = verify_stage(StageRequest.model_validate(raw))
    assert result.local_checks_passed
    assert result.status == "HOLD"
    assert result.reasons == (
        "authenticated_local_release_and_targeted_trials_required",
    )
    assert result.physical_motion_authorized is False
