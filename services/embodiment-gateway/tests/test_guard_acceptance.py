import hashlib
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from furbomek_gateway.guard_acceptance import GuardAcceptance, assess_fixture, main
from furbomek_gateway.guard_replay import (
    ReplayCommand,
    ReplayContext,
    ReplayEnvelope,
    ReplayFixture,
    ReplayStep,
    fixture_mac,
    replay,
)


def command(**changes: str | int) -> ReplayCommand:
    values: dict[str, str | int] = {
        "origin": "owner",
        "boot": "boot-2",
        "session": "session-2",
        "sequence": 1,
        "expires_ms": 200,
        "action": "authorize",
    }
    return ReplayCommand.model_validate(values | changes)


def step(cmd: ReplayCommand, expected: str) -> ReplayStep:
    return ReplayStep.model_validate(
        {
            "event": "command",
            "envelope": ReplayEnvelope(command=cmd, mac=fixture_mac(cmd)),
            "expected": expected,
        }
    )


def fixture(steps: tuple[ReplayStep, ...]) -> ReplayFixture:
    return ReplayFixture(
        schema_version=1,
        scope="abstract_offline_fixture",
        context=ReplayContext(
            origin="owner", boot="boot-2", session="session-2", now_ms=100
        ),
        steps=steps,
    )


@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        ({}, "accepted"),
        ({"origin": "attacker"}, "wrong_origin"),
        ({"boot": "boot-1"}, "stale_session"),
        ({"session": "session-1"}, "stale_session"),
        ({"expires_ms": 100}, "expired"),
        ({"expires_ms": 601}, "expired"),
        ({"sequence": 2}, "wrong_order"),
    ],
)
def test_replay_checks_independent_identity_freshness_and_order(
    changes: dict[str, str | int],
    expected: str,
) -> None:
    assert replay(fixture((step(command(**changes), expected),))) == (expected,)


def test_tampering_is_rejected_before_acceptance() -> None:
    signed = command()
    envelope = ReplayEnvelope(command=command(expires_ms=300), mac=fixture_mac(signed))
    probe = fixture(
        (ReplayStep(event="command", envelope=envelope, expected="integrity"),)
    )
    assert replay(probe) == ("integrity",)


@pytest.mark.parametrize("sequence", [1, 3])
def test_duplicate_and_reordered_commands_are_rejected(sequence: int) -> None:
    probe = fixture(
        (step(command(), "accepted"), step(command(sequence=sequence), "wrong_order"))
    )
    assert replay(probe) == ("accepted", "wrong_order")


@pytest.mark.parametrize("event", ["lost_ack", "power_reset", "cancel"])
def test_uncertainty_latches_against_retry_and_stop_stays_unconditional(
    event: str,
) -> None:
    stop = ReplayEnvelope(
        command=command(action="stop", origin="outsider", boot="old"), mac="0" * 64
    )
    probe = fixture(
        (
            step(command(), "accepted"),
            ReplayStep.model_validate({"event": event, "expected": "uncertain"}),
            step(command(sequence=2), "latched"),
            ReplayStep(event="command", envelope=stop, expected="stopped"),
            step(command(sequence=2), "latched"),
        )
    )
    assert replay(probe) == ("accepted", "uncertain", "latched", "stopped", "latched")


def test_missing_envelope_is_malformed() -> None:
    assert replay(fixture((ReplayStep(event="command", expected="malformed"),))) == (
        "malformed",
    )


@pytest.mark.parametrize("dirty", [False, True])
def test_cli_digest_binding_and_physical_hold(tmp_path: Path, dirty: bool) -> None:
    path = tmp_path / "fixture.json"
    payload = fixture((step(command(), "accepted"),)).model_dump_json()
    _ = path.write_text(payload)
    digest = hashlib.sha256(payload.encode()).hexdigest()
    if dirty:
        _ = path.write_text(payload + " ")
    app = typer.Typer()
    _ = app.command()(main)
    result = CliRunner().invoke(
        app, ["--replay", str(path), "--expected-sha256", digest]
    )
    receipt = GuardAcceptance.model_validate_json(result.stdout)
    assert result.exit_code == (2 if dirty else 0)
    assert receipt.replay == ("HOLD" if dirty else "PASS")
    assert [receipt.installed, receipt.supervised, receipt.unattended] == ["HOLD"] * 3
    assert receipt.physical_motion_authorized is False


@pytest.mark.parametrize(
    "payload", ["{}", "invalid", '{"physical_motion_authorized":true}']
)
def test_malformed_and_misleading_success_inputs_hold(
    tmp_path: Path, payload: str
) -> None:
    path = tmp_path / "fixture.json"
    _ = path.write_text(payload)
    app = typer.Typer()
    _ = app.command()(main)
    result = CliRunner().invoke(
        app,
        [
            "--replay",
            str(path),
            "--expected-sha256",
            hashlib.sha256(payload.encode()).hexdigest(),
        ],
    )
    assert result.exit_code == 2
    assert GuardAcceptance.model_validate_json(result.stdout).replay == "HOLD"


@pytest.mark.parametrize(
    "options",
    [[], ["--run-approved", "/dev/never-open"], ["--replay", "/missing-fixture"]],
)
def test_live_and_missing_admission_hold_without_device_access(
    options: list[str],
) -> None:
    app = typer.Typer()
    _ = app.command()(main)
    result = CliRunner().invoke(app, options)
    assert result.exit_code == 2
    assert (
        GuardAcceptance.model_validate_json(result.stdout).physical_motion_authorized
        is False
    )


def test_claimed_success_does_not_override_actual_rejection(tmp_path: Path) -> None:
    path = tmp_path / "fixture.json"
    payload = fixture((step(command(origin="attacker"), "accepted"),)).model_dump_json()
    _ = path.write_text(payload)
    receipt = assess_fixture(path, hashlib.sha256(payload.encode()).hexdigest())
    assert receipt.replay == "HOLD"
    assert receipt.outcomes == ("wrong_origin",)
