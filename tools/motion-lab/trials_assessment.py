"""Coverage and portable candidate aggregation from accepted optical attempts."""

from statistics import mean

from trials_gateway import MotionProfile, Transform, TrialEvidence
from trials_models import ProfileConditions, ProfileOutcome, Trial, TrialOutcome


def assess_profile(
    conditions: ProfileConditions,
    trials: tuple[Trial, ...],
    outcomes: tuple[TrialOutcome, ...],
) -> ProfileOutcome:
    """Retain rejected denominator; require repetitions and observed strata."""
    pairs = [
        (t, o)
        for t, o in zip(trials, outcomes, strict=True)
        if t.conditions == conditions
    ]
    valid = [(t, o) for t, o in pairs if o.accepted]
    reasons: list[str] = []
    if len(valid) < 10:
        reasons.append("insufficient_repetitions")
    if len(valid) != len(pairs):
        reasons.append("rejected_attempts_require_investigation")
    if conditions.action not in {"active", "sleep"}:
        # Recover heading from pixels, never from trial labels.

        angles: list[float] = []
        for _, outcome in valid:
            angle = outcome.initial_heading_deg
            if angle is not None and all(
                abs((angle - other + 180) % 360 - 180) >= 30 for other in angles
            ):
                angles.append(angle)
        if len(angles) < 3:
            reasons.append("insufficient_orientation_strata")
        bands = conditions.voltage_bands
        if any(bands[i][1] >= bands[i + 1][0] for i in range(len(bands) - 1)):
            reasons.append("voltage_bands_overlap_or_unordered")
        covered = {
            i
            for t, _ in valid
            for i, (a, b) in enumerate(bands)
            if a <= t.observed_voltage <= b
        }
        if len(covered) != len(bands) or (
            len(bands) < 2 and conditions.limited_voltage_evidence is None
        ):
            reasons.append("insufficient_voltage_strata")
    candidate: MotionProfile | None = None
    if not reasons:
        metrics = [
            o.score.metrics
            for _, o in valid
            if o.score is not None and o.score.metrics is not None
        ]
        candidate = MotionProfile(
            schema_version=1,
            robot_revision=conditions.robot_revision,
            installed_sha256=conditions.installed_sha256,
            gait_revision=conditions.gait_revision,
            action=conditions.action,
            start_pose=conditions.start_pose,
            end_pose=conditions.end_pose,
            power_regime=conditions.power_regime,
            load_class=conditions.load_class,
            surface=conditions.surface,
            delta=Transform(
                x_mm=mean(m.x_forward.value for m in metrics),
                y_mm=mean(m.y_left.value for m in metrics),
                yaw_deg=mean(m.yaw_ccw.value for m in metrics),
            ),
            swept_radius_mm=conditions.swept_radius_mm
            + max(m.peak_excursion.value for m in metrics),
            stopping_distance_mm=max(m.post_stop_excursion.value for m in metrics),
            interval_travel_mm=conditions.interval_travel_mm,
            uncertainty_mm=max(
                (m.peak_excursion.uncertainty + m.post_stop_excursion.uncertainty)
                for m in metrics
            ),
            sample_count=len(valid),
            assumptions=(
                "offline_replay_only",
                "independent_clearance_required",
                "voltage-" + "-".join(f"{a}:{b}" for a, b in conditions.voltage_bands),
            ),
            evidence=tuple(
                TrialEvidence(
                    schema_version=1,
                    trial_id=t.trial_id,
                    calibration_id=t.stage.calibration_id,
                    artifact_sha256=o.evidence_sha256,
                    provenance="synthetic"
                    if o.score is not None and o.score.provenance == "synthetic"
                    else "recorded_replay",
                    sample_count=1,
                )
                for t, o in valid
            ),
        )
    return ProfileOutcome(
        conditions=conditions,
        status="HOLD" if reasons else "REPLAY_COMPLETE",
        reasons=tuple(reasons),
        total_attempts=len(pairs),
        valid_trials=len(valid),
        candidate=candidate,
        profile_id=None if candidate is None else candidate.profile_id,
    )
