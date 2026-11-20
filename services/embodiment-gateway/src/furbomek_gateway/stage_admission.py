"""Fail-closed per-step stage checks, with no device or permission writer."""

import hashlib
from math import hypot

from furbomek_gateway.motion_admission import assess_stage
from furbomek_gateway.motion_geometry import Point, Polygon, cross
from furbomek_gateway.stage_models import StageReceipt, StageRequest


def boundary_clearance(polygon: Polygon, center: Point) -> float:
    """Signed clearance to each convex edge; negative means outside."""
    return min(
        cross(a, b, center) / hypot(b[0] - a[0], b[1] - a[1])
        for a, b in zip(
            polygon.vertices, (*polygon.vertices[1:], polygon.vertices[0]), strict=True
        )
    )


def obstacle_clearance(polygon: Polygon, center: Point) -> float:
    """Distance to an obstacle, including finite edge endpoints."""
    if polygon.contains(center):
        return 0.0
    distances: list[float] = []
    for a, b in zip(
        polygon.vertices, (*polygon.vertices[1:], polygon.vertices[0]), strict=True
    ):
        dx, dy = b[0] - a[0], b[1] - a[1]
        t = max(
            0.0,
            min(
                1.0,
                ((center[0] - a[0]) * dx + (center[1] - a[1]) * dy)
                / (dx * dx + dy * dy),
            ),
        )
        distances.append(hypot(center[0] - a[0] - t * dx, center[1] - a[1] - t * dy))
    return min(distances)


def verify_stage(request: StageRequest) -> StageReceipt:
    """Check exact evidence and conservative excursion disk for one selected move."""
    context = request.context
    p, s, c = context.profile, context.stage, context.calibration
    survey, containment, current = request.survey, request.containment, request.current
    # The disk includes the entire measured swept envelope, stop/interval margins,
    # and nominal displacement. It is conservative for arbitrary heading/turns.
    radius = (
        p.clearance_mm
        + hypot(p.delta.x_mm, p.delta.y_mm)
        + c.translation_error_mm
        + request.clearance_margin_mm
    )
    center = (current.start.x_mm, current.start.y_mm)
    checks = (
        (not request.invalidated, "stage_invalidated"),
        (p.profile_id in request.approved_profile_ids, "profile_not_selected"),
        (
            survey.stage_id == s.stage_id
            and survey.stage_frame_id == s.stage_frame_id
            and survey.revision == current.survey_revision
            and survey.usable_polygon == s.usable_polygon
            and survey.surface == s.surface
            and survey.digest == s.survey_sha256,
            "survey_changed",
        ),
        (
            containment.stage_id == s.stage_id
            and containment.survey_sha256 == survey.digest
            and containment.digest == s.containment_evidence_sha256
            and containment.source_sha256 != survey.source_sha256,
            "containment_binding_mismatch",
        ),
        (
            all(
                containment.contained_polygon.contains(v)
                for v in s.usable_polygon.vertices
            ),
            "containment_incomplete",
        ),
        (
            current.robot_revision == p.robot_revision
            and current.installed_sha256 == p.installed_sha256
            and current.gait_revision == p.gait_revision,
            "current_robot_changed",
        ),
        (
            current.power_regime == p.power_regime
            and current.load_class == p.load_class
            and current.pose == p.start_pose,
            "current_profile_conditions_changed",
        ),
        (current.footprint_radius_mm <= p.swept_radius_mm, "footprint_outside_profile"),
        (
            current.surface == s.surface and p.surface.covers(current.surface),
            "current_surface_changed",
        ),
        (
            0 <= context.now_ms - current.observed_ms <= current.maximum_age_ms,
            "current_observation_stale",
        ),
        (
            boundary_clearance(s.usable_polygon, center) > radius,
            "step_boundary_clearance",
        ),
        (
            all(obstacle_clearance(o, center) > radius for o in survey.obstacles),
            "step_obstacle_clearance",
        ),
    )
    reasons = list(assess_stage(context).hold_reasons)
    reasons.extend(reason for passed, reason in checks if not passed)
    replay = request.mode == "replay_comparison"
    if replay and request.comparison_id is None:
        reasons.append("named_replay_comparison_required")
    local_pass = not reasons
    if not replay:
        reasons.append("authenticated_local_release_and_targeted_trials_required")
    return StageReceipt(
        status="REPLAY_ELIGIBLE" if replay and local_pass else "HOLD",
        local_checks_passed=local_pass,
        reasons=tuple(reasons),
        request_sha256=hashlib.sha256(request.model_dump_json().encode()).hexdigest(),
        profile_id=p.profile_id,
        stage_id=s.stage_id,
        required_clearance_mm=radius,
    )
