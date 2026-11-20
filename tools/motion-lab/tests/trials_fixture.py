"""Synthetic whole-set camera projections; never installed hardware measurements."""

import hashlib

from score_models import ExpectedMotion, ScoreInput
from tests.score_fixture import replay
from trials_gateway import Polygon, StageProfile, SurfaceClass
from trials_models import ProfileConditions, Trial, TrialManifest


def catalog() -> TrialManifest:
    surface = SurfaceClass(
        material_id="synthetic-coupon",
        finish_id="matte",
        slope_deg=(0, 1),
        static_traction=(0.4, 0.8),
    )
    profiles: list[ProfileConditions] = []
    trials: list[Trial] = []
    for action, target in (
        ("forward", (20, 0, 0, 0)),
        ("backward", (-20, 0, 0, 0)),
        ("left", (0, 20, 0, 0)),
        ("right", (0, -20, 0, 0)),
        ("turn_left", (0, 0, 20, 0)),
        ("turn_right", (0, 0, -20, 0)),
        ("active", (0, 0, 0, 15)),
        ("sleep", (0, 0, 0, -15)),
    ):
        conditions = ProfileConditions.model_validate(
            {
                "action": action,
                "start_pose": "synthetic-start",
                "end_pose": "synthetic-end",
                "robot_revision": "synthetic-robot",
                "installed_sha256": "a" * 64,
                "gait_revision": "synthetic-gait",
                "power_regime": "synthetic-voltage",
                "load_class": "synthetic-load",
                "surface": surface,
                "voltage_bands": ((6, 6.5), (7, 7.5)),
                "swept_radius_mm": 10,
                "interval_travel_mm": 2,
            }
        )
        profiles.append(conditions)
        for i in range(10):
            data = replay(
                ExpectedMotion(
                    x_forward_mm=target[0],
                    y_left_mm=target[1],
                    yaw_ccw_deg=target[2],
                    height_up_mm=target[3],
                ),
                heading=(i % 3) * 45,
            )
            raw = data.model_dump()
            for frame in raw["frames"]:
                frame["content_sha256"] = hashlib.sha256(
                    f"synthetic-exposure-{action}-{i}-{frame['sequence']}".encode()
                ).hexdigest()
            data = ScoreInput.model_validate(raw)
            stage = StageProfile(
                schema_version=1,
                stage_id=data.calibration.stage_id,
                stage_frame_id="synthetic-frame",
                calibration_id=data.calibration_id,
                profile_id="candidate-unassigned",
                robot_revision=conditions.robot_revision,
                installed_sha256=conditions.installed_sha256,
                surface=surface,
                usable_polygon=Polygon(
                    vertices=((-200, -200), (200, -200), (200, 200), (-200, 200))
                ),
                containment_evidence_sha256="b" * 64,
                hazards=(),
                survey_sha256="c" * 64,
            )
            trials.append(
                Trial(
                    trial_id=f"synthetic-{action}-{i}",
                    conditions=conditions,
                    stage=stage,
                    stage_start_mm=(0, 0),
                    independent_clearance_sha256="d" * 64,
                    independent_cutoff_sha256="e" * 64,
                    observed_surface=surface,
                    observed_voltage=6.25 if i % 2 == 0 else 7.25,
                    start_pose=conditions.start_pose,
                    end_pose=conditions.end_pose,
                    normal_disarm=True,
                    score=data,
                )
            )
    return TrialManifest(
        schema_version=1, profiles=tuple(profiles), trials=tuple(trials)
    )


def forward_catalog() -> TrialManifest:
    """One profile for focused rejection tests; whole-set test owns all verbs."""
    data = catalog()
    return TrialManifest(
        schema_version=1, profiles=data.profiles[:1], trials=data.trials[:10]
    )
