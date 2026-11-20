"""Whole-set offline replay catalog. Physical dispatch is unconditionally held."""

import hashlib
from pathlib import Path
from typing import get_args

from score import score_run
from trials_assessment import assess_profile
from trials_checks import check_trial, observed_heading
from trials_gateway import ActionName
from trials_models import CatalogReceipt, TrialManifest, TrialOutcome


def replay_catalog(manifest: TrialManifest, directory: Path) -> CatalogReceipt:
    """Recompute optical results; caller-supplied protocol success is insufficient."""
    outcomes: list[TrialOutcome] = []
    forward_proven = False
    seen: set[str] = set()
    exposures: set[tuple[str, ...]] = set()
    for trial in manifest.trials:
        result = None if trial.score is None else score_run(trial.score, directory)
        reasons = (
            ("optical_measurement_unavailable",)
            if result is None
            else check_trial(trial, result)
        )
        if trial.trial_id in seen:
            reasons += ("duplicate_trial_id",)
        seen.add(trial.trial_id)
        if trial.score is not None:
            frames = tuple(f.content_sha256 for f in trial.score.frames)
            if frames in exposures:
                reasons += ("reused_camera_evidence",)
            exposures.add(frames)
        if trial.conditions not in manifest.profiles:
            reasons += ("undeclared_profile",)
        if trial.conditions.action != "forward" and not forward_proven:
            reasons += ("calibrated_forward_required_first",)
        if trial.conditions.action == "forward" and not reasons:
            forward_proven = True
        outcomes.append(
            TrialOutcome(
                trial_id=trial.trial_id,
                accepted=not reasons,
                reasons=reasons,
                evidence_sha256=hashlib.sha256(
                    trial.model_dump_json().encode()
                ).hexdigest(),
                score=result,
                initial_heading_deg=observed_heading(trial.score, directory)
                if trial.score is not None and not reasons
                else None,
            )
        )
    profiles = tuple(
        assess_profile(p, manifest.trials, tuple(outcomes)) for p in manifest.profiles
    )
    catalog_reasons: list[str] = []
    if {p.action for p in manifest.profiles} != set(get_args(ActionName.__value__)):
        catalog_reasons.append("whole_set_incomplete")
    if len({p.model_dump_json() for p in manifest.profiles}) != len(manifest.profiles):
        catalog_reasons.append("duplicate_profile")
    if any(not o.accepted for o in outcomes) or any(
        p.status == "HOLD" for p in profiles
    ):
        catalog_reasons.append("trial_or_profile_hold")
    return CatalogReceipt(
        status="HOLD" if catalog_reasons else "REPLAY_COMPLETE",
        reasons=tuple(catalog_reasons),
        profiles=profiles,
        trials=tuple(outcomes),
    )


if __name__ == "__main__":
    from trials_cli import run_cli

    run_cli(replay_catalog)
