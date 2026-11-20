import subprocess
import sys
from pathlib import Path

import pytest

from score_models import ExpectedMotion
from tests.score_fixture import replay
from tests.trials_fixture import catalog, forward_catalog
from trials import replay_catalog
from trials_models import CatalogReceipt, TrialManifest


def test_all_verbs_require_optical_progress_and_remain_physically_held(
    tmp_path: Path,
) -> None:
    result = replay_catalog(catalog(), tmp_path)
    assert result.status == "REPLAY_COMPLETE", [
        (p.status, p.reasons) for p in result.profiles
    ]
    assert [p.valid_trials for p in result.profiles] == [10] * 8
    assert result.physical_motion_authorized is False
    assert result.supervised_status == result.unattended_status == "HOLD"
    assert all(
        p.candidate is not None and p.candidate.evidence[0].provenance == "synthetic"
        for p in result.profiles
    )


@pytest.mark.parametrize(
    ("actual", "reason"),
    [
        ((0, 0, 0, 0), "optical_no_travel"),
        ((10, 0, 0, 0), "optical_partial"),
        ((-20, 0, 0, 0), "optical_unexpected"),
        ((20, 0, 20, 0), "mixed_motion"),
    ],
)
def test_protocol_completion_does_not_count_failed_motion(
    tmp_path: Path,
    actual: tuple[float, float, float, float],
    reason: str,
) -> None:
    raw = forward_catalog().model_dump()
    raw["trials"][0]["score"] = replay(
        ExpectedMotion(x_forward_mm=20, y_left_mm=0, yaw_ccw_deg=0, height_up_mm=0),
        ExpectedMotion(
            x_forward_mm=actual[0],
            y_left_mm=actual[1],
            yaw_ccw_deg=actual[2],
            height_up_mm=actual[3],
        ),
    ).model_dump()
    result = replay_catalog(TrialManifest.model_validate(raw), tmp_path)
    assert result.status == "HOLD"
    assert reason in result.trials[0].reasons
    assert result.profiles[0].total_attempts == 10
    assert result.profiles[0].valid_trials == 9


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("normal_disarm", False, "guard_completion_or_disarm_missing"),
        ("score", None, "optical_measurement_unavailable"),
        ("start_pose", "other", "pose_mismatch"),
        ("stage_start_mm", [199, 0], "insufficient_independent_clearance"),
        ("observed_voltage", 9, "voltage_outside_tested_range"),
    ],
)
def test_rejected_attempt_retains_denominator(
    tmp_path: Path,
    field: str,
    *,
    value: str | bool | float | list[int] | None,
    reason: str,
) -> None:
    raw = forward_catalog().model_dump()
    raw["trials"][0][field] = value
    result = replay_catalog(TrialManifest.model_validate(raw), tmp_path)
    assert reason in result.trials[0].reasons
    assert result.profiles[0].valid_trials == 9
    assert result.profiles[0].total_attempts == 10


def test_surface_mismatch_holds_even_with_valid_motion(tmp_path: Path) -> None:
    raw = forward_catalog().model_dump()
    raw["trials"][0]["observed_surface"]["static_traction"] = [0.2, 0.3]
    result = replay_catalog(TrialManifest.model_validate(raw), tmp_path)
    assert "surface_mismatch" in result.trials[0].reasons


def test_missing_repetitions_and_whole_set_are_visible(tmp_path: Path) -> None:
    raw = forward_catalog().model_dump()
    raw["trials"] = raw["trials"][:9]
    raw["profiles"] = raw["profiles"][:1]
    result = replay_catalog(TrialManifest.model_validate(raw), tmp_path)
    assert result.reasons == ("whole_set_incomplete", "trial_or_profile_hold")
    assert "insufficient_repetitions" in result.profiles[0].reasons


def test_voltage_strata_cannot_be_inferred_from_labels(tmp_path: Path) -> None:
    raw = forward_catalog().model_dump()
    for trial in raw["trials"]:
        trial["observed_voltage"] = 6.25
    result = replay_catalog(TrialManifest.model_validate(raw), tmp_path)
    assert "insufficient_voltage_strata" in result.profiles[0].reasons


def test_forward_must_be_proven_before_other_verbs(tmp_path: Path) -> None:
    raw = catalog().model_dump()
    raw["trials"] = raw["trials"][10:] + raw["trials"][:10]
    result = replay_catalog(TrialManifest.model_validate(raw), tmp_path)
    assert "calibrated_forward_required_first" in result.trials[0].reasons


def test_duplicate_exposures_do_not_manufacture_repetitions(tmp_path: Path) -> None:
    raw = forward_catalog().model_dump()
    raw["trials"][1]["score"] = raw["trials"][0]["score"]
    result = replay_catalog(TrialManifest.model_validate(raw), tmp_path)
    assert "reused_camera_evidence" in result.trials[1].reasons
    assert result.profiles[0].valid_trials == 9


def test_orientation_strata_are_recovered_from_pixels(tmp_path: Path) -> None:
    raw = forward_catalog().model_dump()
    for trial in raw["trials"]:
        for target, source in zip(
            trial["score"]["frames"], raw["trials"][0]["score"]["frames"], strict=True
        ):
            target["observation"] = source["observation"]
    result = replay_catalog(TrialManifest.model_validate(raw), tmp_path)
    assert "insufficient_orientation_strata" in result.profiles[0].reasons


def test_semantic_verb_cannot_claim_another_axis(tmp_path: Path) -> None:
    raw = forward_catalog().model_dump()
    raw["trials"][0]["score"] = replay(
        ExpectedMotion(
            x_forward_mm=0,
            y_left_mm=20,
            yaw_ccw_deg=0,
            height_up_mm=0,
        )
    ).model_dump()
    result = replay_catalog(TrialManifest.model_validate(raw), tmp_path)
    assert "semantic_target_mismatch" in result.trials[0].reasons


@pytest.mark.parametrize(
    ("args", "reason"),
    [
        ([], "replay_or_approval_missing"),
        (
            [
                "--run-approved",
                "missing-approval.json",
                "--replay",
                "missing-replay.json",
            ],
            "physical_dispatch_unavailable",
        ),
        (["--replay", "missing-replay.json"], "invalid_trial_manifest"),
    ],
)
def test_cli_holds_without_opening_approval_paths(args: list[str], reason: str) -> None:
    result = subprocess.run(
        [sys.executable, str(Path(__file__).parents[1] / "trials.py"), *args],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 2
    receipt = CatalogReceipt.model_validate_json(result.stdout)
    assert reason in receipt.reasons
    assert receipt.physical_motion_authorized is False
