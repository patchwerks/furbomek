"""Offline Guard evidence gate. This command never opens a hardware transport."""

import hashlib
from pathlib import Path
from typing import Annotated, Literal

import typer
from pydantic import ValidationError

from furbomek_gateway.guard_replay import ReplayFixture, replay
from furbomek_gateway.motion_geometry import Contract, Digest


class GuardAcceptance(Contract):
    """Scope-separated receipt; fixture success cannot authorize physical motion."""

    schema_version: Literal[1] = 1
    scope: Literal["offline_only"] = "offline_only"
    replay: Literal["PASS", "HOLD"]
    installed: Literal["HOLD"] = "HOLD"
    supervised: Literal["HOLD"] = "HOLD"
    unattended: Literal["HOLD"] = "HOLD"
    physical_motion_authorized: Literal[False] = False
    fixture_sha256: Digest | None = None
    outcomes: tuple[str, ...] = ()
    hold_reasons: tuple[str, ...] = (
        "current_installed_identity_unverified",
        "installed_robot_origin_integrity_freshness_unqualified",
        "independent_measured_cutoff_missing",
        "fresh_physical_admission_missing",
    )


def assess_fixture(path: Path, expected_sha256: str) -> GuardAcceptance:
    """Bind reviewed fixture bytes to a separate expected digest before replay."""
    payload = path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != expected_sha256:
        return GuardAcceptance(replay="HOLD", hold_reasons=("fixture_digest_mismatch",))
    fixture = ReplayFixture.model_validate_json(payload)
    outcomes = replay(fixture)
    success = outcomes == tuple(step.expected for step in fixture.steps)
    return GuardAcceptance(
        replay="PASS" if success else "HOLD",
        fixture_sha256=digest,
        outcomes=outcomes,
    )


def main(
    replay_path: Annotated[Path | None, typer.Option("--replay")] = None,
    expected_sha256: Annotated[str, typer.Option()] = "",
    run_approved: Annotated[Path | None, typer.Option("--run-approved")] = None,
) -> None:
    """Replay reviewed data, or HOLD live requests pending physical qualification.

    Exit zero means only that offline outcomes matched. Installed/supervised and
    unattended admission remain HOLD, including with a purported approval file.
    """
    receipt = GuardAcceptance(replay="HOLD")
    if run_approved is not None:
        receipt = GuardAcceptance(
            replay="HOLD",
            hold_reasons=("live_probe_not_admitted",),
        )
    elif replay_path is not None:
        try:
            receipt = assess_fixture(replay_path, expected_sha256)
        except (OSError, ValidationError):
            receipt = GuardAcceptance(
                replay="HOLD",
                hold_reasons=("missing_or_malformed_fixture",),
            )
    typer.echo(receipt.model_dump_json())
    raise typer.Exit(code=0 if receipt.replay == "PASS" else 2)


if __name__ == "__main__":
    typer.run(main)
