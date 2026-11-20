"""Analytic synthetic stage fixtures; no physical dimensions or containment claims."""

import hashlib
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from calibration_models import CalibrationInput, Frame, Pose, ValidationPose
from calibration_solver import calibrate
from stage_gateway import ContainmentCheck, Polygon, StageSurvey, Transform
from stage_verification import StageBundle
from tests.fixture_scene import rotation, scene
from tests.trials_fixture import forward_catalog
from trials import replay_catalog
from trials_gateway import MotionProfile


def calibration(view: int) -> CalibrationInput:
    """Independent Brown projection of surveyed corners in two camera poses."""
    base = scene(view)
    lower, upper = (-80, 200) if view == 0 else (-120, 240)
    matrix = rotation((12, -18, 5) if view == 0 else (-8, 8, -12))
    translation = np.array([-60, -60, 600.0 if view == 0 else 900.0])
    corners = np.array([[-20, -20, 0], [20, -20, 0], [20, 20, 0], [-20, 20, 0]])

    def project(points: NDArray[np.float64]) -> list[list[float]]:
        xy = points[:, :2] / points[:, 2:]
        x, y = xy[:, 0], xy[:, 1]
        r2 = x * x + y * y
        radial = 1 - 0.18 * r2 + 0.04 * r2 * r2 - 0.006 * r2 * r2 * r2
        u = 580 * (x * radial + 0.002 * x * y - 0.001 * (r2 + 2 * x * x)) + 318
        v = 575 * (y * radial + 0.001 * (r2 + 2 * y * y) - 0.002 * x * y) + 241
        return np.column_stack((u, v)).tolist()

    def frame(pose: Pose) -> Frame:
        markers = [
            {
                "marker_id": i,
                "corners": project((corners + center) @ matrix.T + translation),
            }
            for i, center in enumerate(
                ((0, 0, 0), (120, 0, 0), (120, 120, 0), (0, 120, 0))
            )
        ]
        points = (
            corners @ rotation((0, 0, pose.yaw_deg)).T
            + [pose.x_mm, pose.y_mm, pose.z_mm]
        ) @ matrix.T + translation
        markers.append({"marker_id": 10, "corners": project(points)})
        return Frame.model_validate(base.current.model_dump() | {"markers": markers})

    poses = [
        Pose(x_mm=x, y_mm=y, z_mm=-65, yaw_deg=yaw)
        for x, y, yaw in (
            (lower, lower, 0),
            (upper, lower, 15),
            (upper, upper, 30),
            (lower, upper, -20),
        )
    ]
    current = Pose(x_mm=60, y_mm=60, z_mm=-65, yaw_deg=0)
    return CalibrationInput.model_validate(
        base.model_dump()
        | {
            "stage_id": f"synthetic-stage-{view}",
            "validations": [ValidationPose(frame=frame(p), expected=p) for p in poses],
            "current": frame(current),
            "reference": frame(current),
        }
    )


def bundle(view: int, profile: MotionProfile) -> StageBundle:
    """Build explicit synthetic surveys separately from the optical input."""
    data = calibration(view)
    result = calibrate(data, 10000)
    if result.status == "HOLD":
        raise RuntimeError(result.reasons)
    result = result.model_copy(
        update={
            "input_sha256": hashlib.sha256(data.model_dump_json().encode()).hexdigest()
        }
    )
    transform = Transform(
        x_mm=0 if view == 0 else 500,
        y_mm=0 if view == 0 else -200,
        yaw_deg=0 if view == 0 else 90,
    )
    lower, upper = (-60, 180) if view == 0 else (-100, 220)
    polygon = Polygon(
        vertices=tuple(
            transform.apply(p)
            for p in ((lower, lower), (upper, lower), (upper, upper), (lower, upper))
        )
    )
    survey = StageSurvey(
        stage_id=data.stage_id,
        revision="synthetic-survey-v1",
        stage_frame_id=data.reference_revision,
        usable_polygon=polygon,
        surface=profile.surface,
        obstacles=(),
        source_sha256=hashlib.sha256(f"synthetic-surveyor-{view}".encode()).hexdigest(),
    )
    containment = ContainmentCheck(
        stage_id=data.stage_id,
        survey_sha256=survey.digest,
        contained_polygon=polygon,
        source_sha256=hashlib.sha256(
            f"synthetic-independent-containment-{view}".encode()
        ).hexdigest(),
    )
    start = transform.apply((60, 60))
    return StageBundle.model_validate(
        {
            "calibration_input": data,
            "calibration_receipt": result,
            "request": {
                "schema_version": 1,
                "mode": "replay_comparison",
                "comparison_id": "synthetic-two-stages-v1",
                "context": {
                    "profile": profile,
                    "now_ms": 10000,
                    "observation_revision": data.camera_revision,
                    "stage": {
                        "schema_version": 1,
                        "stage_id": data.stage_id,
                        "stage_frame_id": data.reference_revision,
                        "calibration_id": f"synthetic-calibration-{view}",
                        "profile_id": profile.profile_id,
                        "robot_revision": profile.robot_revision,
                        "installed_sha256": profile.installed_sha256,
                        "surface": profile.surface,
                        "usable_polygon": polygon,
                        "containment_evidence_sha256": containment.digest,
                        "hazards": (),
                        "survey_sha256": survey.digest,
                    },
                    "calibration": {
                        "schema_version": 1,
                        "calibration_id": f"synthetic-calibration-{view}",
                        "stage_id": data.stage_id,
                        "stage_frame_id": data.reference_revision,
                        "observation_revision": data.camera_revision,
                        "observation_to_stage": transform,
                        "coverage": polygon,
                        "valid_from_ms": 10000,
                        "valid_until_ms": 10600,
                        "translation_error_mm": 1.0,
                        "yaw_error_deg": 1.0,
                        "minimum_translation_mm": data.minimum_translation_mm,
                        "minimum_yaw_deg": data.minimum_yaw_deg,
                        "independent_validation_sha256": hashlib.sha256(
                            result.model_dump_json().encode()
                        ).hexdigest(),
                        "observable_poses": [profile.start_pose, profile.end_pose],
                    },
                },
                "survey": survey,
                "containment": containment,
                "current": {
                    "robot_revision": profile.robot_revision,
                    "installed_sha256": profile.installed_sha256,
                    "gait_revision": profile.gait_revision,
                    "power_regime": profile.power_regime,
                    "load_class": profile.load_class,
                    "pose": profile.start_pose,
                    "surface": profile.surface,
                    "footprint_radius_mm": 10.0,
                    "start": {
                        "x_mm": start[0],
                        "y_mm": start[1],
                        "yaw_deg": transform.yaw_deg,
                    },
                    "observed_ms": 10000,
                    "maximum_age_ms": 600,
                    "survey_revision": survey.revision,
                },
                "approved_profile_ids": [profile.profile_id],
                "invalidated": False,
                "clearance_margin_mm": 1.0,
            },
        }
    )


def write_fixtures(directory: Path) -> None:
    """Regenerate the selected Task8 candidate using its actual optical scorer."""
    catalog = replay_catalog(forward_catalog(), directory)
    profile = catalog.profiles[0].candidate
    if profile is None:
        raise RuntimeError(catalog.profiles[0].reasons)
    for view in (0, 1):
        _ = (directory / f"stage-{view}.json").write_text(
            bundle(view, profile).model_dump_json(indent=2) + "\n"
        )
