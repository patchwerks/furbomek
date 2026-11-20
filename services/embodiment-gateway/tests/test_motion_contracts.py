"""Portable evidence and independent stage eligibility boundaries."""

import json

import pytest
from pydantic import ValidationError

from furbomek_gateway.motion_admission import AdmissionContext, assess_stage
from furbomek_gateway.motion_contracts import (
    MotionProfile,
    ObservationCalibration,
    StageProfile,
)


def profile() -> MotionProfile:
    return MotionProfile.model_validate_json(
        json.dumps(
            {
                "schema_version": 1,
                "robot_revision": "fixture-robot-v1",
                "installed_sha256": "a" * 64,
                "gait_revision": "two-phase-v1",
                "action": "left",
                "start_pose": "active",
                "end_pose": "active",
                "power_regime": "fixture-6.5-8.6V",
                "load_class": "fixture-head",
                "surface": {
                    "material_id": "wood",
                    "finish_id": "matte",
                    "slope_deg": [0, 2],
                    "static_traction": [0.4, 0.8],
                },
                "delta": {"x_mm": 0, "y_mm": 30, "yaw_deg": 0},
                "swept_radius_mm": 200,
                "stopping_distance_mm": 10,
                "interval_travel_mm": 5,
                "uncertainty_mm": 2,
                "sample_count": 10,
                "assumptions": ["fixture-only"],
                "evidence": [
                    {
                        "schema_version": 1,
                        "trial_id": "trial-a",
                        "calibration_id": "cal-a",
                        "artifact_sha256": "b" * 64,
                        "provenance": "synthetic",
                        "sample_count": 10,
                    }
                ],
            }
        )
    )


def stage_bundle(stage_id: str = "stage-a", size: int = 500) -> AdmissionContext:
    p = profile()
    polygon = {"vertices": [[0, 0], [size, 0], [size, size], [0, size]]}
    calibration = ObservationCalibration.model_validate(
        {
            "schema_version": 1,
            "calibration_id": "cal-" + stage_id,
            "stage_id": stage_id,
            "observation_revision": "view-1",
            "stage_frame_id": "anchor-" + stage_id,
            "observation_to_stage": {
                "x_mm": size - 400,
                "y_mm": 450 - size,
                "yaw_deg": size * 0.18 - 90,
            },
            "coverage": polygon,
            "valid_from_ms": 1000,
            "valid_until_ms": 2000,
            "translation_error_mm": 1,
            "yaw_error_deg": 1,
            "minimum_translation_mm": 20,
            "minimum_yaw_deg": 10,
            "independent_validation_sha256": "c" * 64,
            "observable_poses": ["active"],
        }
    )
    stage = StageProfile.model_validate(
        {
            "schema_version": 1,
            "stage_id": stage_id,
            "stage_frame_id": "anchor-" + stage_id,
            "calibration_id": calibration.calibration_id,
            "profile_id": p.profile_id,
            "robot_revision": p.robot_revision,
            "installed_sha256": p.installed_sha256,
            "surface": p.surface.model_dump(),
            "usable_polygon": polygon,
            "containment_evidence_sha256": "d" * 64,
            "hazards": [],
            "survey_sha256": "e" * 64,
        }
    )
    return AdmissionContext(
        profile=p,
        stage=stage,
        calibration=calibration,
        observation_revision="view-1",
        now_ms=1500,
    )


def test_portable_profile_survives_larger_rotated_stage() -> None:
    a, b = stage_bundle(), stage_bundle("stage-b", 1000)
    assert a.profile.profile_id == b.profile.profile_id
    assert a.stage.stage_id != b.stage.stage_id
    assert a.calibration.calibration_id != b.calibration.calibration_id
    assert b.profile.evidence[0].calibration_id == "cal-a"
    assert assess_stage(b).decision == "eligible"
    assert b.calibration.observation_to_stage.apply((10, 0)) == pytest.approx(
        (600, -540)
    )


@pytest.mark.parametrize(
    "patch",
    [
        {"units": "cm"},
        {"delta": {"x_mm": 0, "y_mm": -30, "yaw_deg": 0}},
        {"swept_radius_mm": float("nan")},
        {"schema_version": 2},
        {
            "surface": {
                "material_id": "wood",
                "finish_id": "matte",
                "slope_deg": [2, 0],
                "static_traction": [0.4, 0.8],
            }
        },
    ],
)
def test_portable_profile_rejects_malformed_measurements(
    patch: dict[str, str | int | float | dict[str, str | int | list[float]]],
) -> None:
    with pytest.raises(ValidationError):
        _ = MotionProfile.model_validate(profile().model_dump() | patch)


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ({"now_ms": 2000}, "calibration_expired"),
        ({"now_ms": 999}, "calibration_expired"),
        ({"observation_revision": "moved-camera"}, "observation_changed"),
    ],
)
def test_stage_admission_refuses_stale_context(
    change: dict[str, int | str], reason: str
) -> None:
    context = AdmissionContext.model_validate(stage_bundle().model_dump() | change)
    assert reason in assess_stage(context).hold_reasons
    assert assess_stage(context).decision == "hold"


def test_stage_admission_refuses_cropped_coverage() -> None:
    context = stage_bundle()
    data = context.calibration.model_dump()
    data["coverage"] = {"vertices": [[0, 0], [100, 0], [100, 100], [0, 100]]}
    calibration = ObservationCalibration.model_validate(data)
    context = AdmissionContext.model_validate(
        context.model_dump() | {"calibration": calibration}
    )
    assert assess_stage(context).hold_reasons == ("coverage_incomplete",)


@pytest.mark.parametrize(
    "vertices",
    [
        [[0, 0], [1, 1], [0, 1], [1, 0]],
        [[0, 0], [1, 0], [2, 0]],
        [[0, 0], [1, 0], [1, float("inf")]],
    ],
)
def test_stage_admission_rejects_malformed_polygon(vertices: list[list[float]]) -> None:
    with pytest.raises(ValidationError):
        _ = StageProfile.model_validate(
            stage_bundle().stage.model_dump()
            | {"usable_polygon": {"vertices": vertices}}
        )


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("calibration_id", "other", "calibration_binding_mismatch"),
        ("profile_id", "other", "profile_changed"),
        ("robot_revision", "other", "robot_changed"),
        ("hazards", ["edge-gap"], "unresolved_hazards"),
    ],
)
def test_stage_admission_preserves_explicit_holds(
    field: str, value: str | list[str], reason: str
) -> None:
    context = stage_bundle()
    stage = StageProfile.model_validate(context.stage.model_dump() | {field: value})
    context = AdmissionContext.model_validate(context.model_dump() | {"stage": stage})
    assert assess_stage(context).hold_reasons == (reason,)


@pytest.mark.parametrize(
    "patch",
    [
        {"translation_error_mm": 5.01},
        {"yaw_error_deg": 2.01},
        {"minimum_translation_mm": 4},
        {"minimum_yaw_deg": 4},
        {"valid_until_ms": 1000},
        {"valid_from_ms": True},
    ],
)
def test_stage_admission_rejects_invalid_calibration(
    patch: dict[str, float | int | bool],
) -> None:
    with pytest.raises(ValidationError):
        _ = ObservationCalibration.model_validate(
            stage_bundle().calibration.model_dump() | patch
        )


def test_stage_admission_holds_unobservable_pose() -> None:
    context = stage_bundle()
    calibration = ObservationCalibration.model_validate(
        context.calibration.model_dump() | {"observable_poses": ["sleep"]}
    )
    context = AdmissionContext.model_validate(
        context.model_dump() | {"calibration": calibration}
    )
    assert assess_stage(context).hold_reasons == ("posture_unobservable",)


def test_stage_admission_holds_surface_outside_tested_interval() -> None:
    context = stage_bundle()
    surface = context.stage.surface.model_dump() | {"static_traction": [0.3, 0.8]}
    stage = StageProfile.model_validate(
        context.stage.model_dump() | {"surface": surface}
    )
    context = AdmissionContext.model_validate(context.model_dump() | {"stage": stage})
    assert assess_stage(context).hold_reasons == ("surface_outside_tested_range",)


def test_portable_profile_json_roundtrip_retains_evidence() -> None:
    original = profile()
    restored = MotionProfile.model_validate_json(original.model_dump_json())
    assert restored.evidence[0].artifact_sha256 == "b" * 64
    assert restored.profile_id == original.profile_id
    assert restored.clearance_mm == 217
    assert assess_stage(stage_bundle()).physical_motion_authorized is False
