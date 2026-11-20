"""Abstract offline authentication probe; not the installed Guard wire protocol.

The public fixture key has no production trust. No caller of this module may
use its result as authorization for a serial write or physical power admission.
"""

import hashlib
import hmac
from typing import Annotated, Final, Literal, assert_never

from pydantic import Field

from furbomek_gateway.motion_geometry import Contract, Digest, Identifier

type Tick = Annotated[int, Field(ge=0, strict=True)]
FIXTURE_KEY: Final = b"public-offline-guard-fixture-only-v1"


class ReplayCommand(Contract):
    """Signed, bounded abstract command, never encoded for a device."""

    origin: Identifier
    boot: Identifier
    session: Identifier
    sequence: Annotated[int, Field(gt=0, strict=True)]
    expires_ms: Tick
    action: Literal["authorize", "stop"]


class ReplayEnvelope(Contract):
    """Integrity evidence for the abstract probe only."""

    command: ReplayCommand
    mac: Digest


class ReplayContext(Contract):
    """Independent expectations, rather than identity supplied by the command."""

    origin: Identifier
    boot: Identifier
    session: Identifier
    now_ms: Tick


class ReplayStep(Contract):
    """An input event and expected observable rejection/acceptance."""

    event: Literal["command", "lost_ack", "power_reset", "cancel"]
    envelope: ReplayEnvelope | None = None
    expected: Literal[
        "accepted",
        "stopped",
        "wrong_origin",
        "integrity",
        "stale_session",
        "expired",
        "wrong_order",
        "latched",
        "uncertain",
        "malformed",
    ]


class ReplayFixture(Contract):
    """Strict portable fixture schema with no hardware routes or admission flags."""

    schema_version: Literal[1]
    scope: Literal["abstract_offline_fixture"]
    context: ReplayContext
    steps: Annotated[tuple[ReplayStep, ...], Field(min_length=1, max_length=1000)]


def fixture_mac(command: ReplayCommand) -> str:
    """Authenticate canonical fixture bytes with a deliberately public test key."""
    return hmac.new(
        FIXTURE_KEY,
        command.model_dump_json().encode(),
        hashlib.sha256,
    ).hexdigest()


def replay(fixture: ReplayFixture) -> tuple[str, ...]:
    """Apply rejection ordering; uncertain mutations latch until a fresh probe."""
    context = fixture.context
    sequence = 0
    latched = False
    outcomes: list[str] = []
    for step in fixture.steps:
        match step.event:
            case "lost_ack" | "power_reset" | "cancel":
                latched = True
                outcomes.append("uncertain")
            case "command":
                envelope = step.envelope
                if envelope is None:
                    outcomes.append("malformed")
                    continue
                command = envelope.command
                match command.action:
                    case "stop":
                        latched = True
                        outcomes.append("stopped")
                        continue
                    case "authorize":
                        pass
                    case _:
                        assert_never(command.action)
                checks = (
                    (not latched, "latched"),
                    (command.origin == context.origin, "wrong_origin"),
                    (
                        hmac.compare_digest(envelope.mac, fixture_mac(command)),
                        "integrity",
                    ),
                    (
                        command.boot == context.boot
                        and command.session == context.session,
                        "stale_session",
                    ),
                    (
                        context.now_ms < command.expires_ms <= context.now_ms + 500,
                        "expired",
                    ),
                    (command.sequence == sequence + 1, "wrong_order"),
                )
                reason = next((reason for passed, reason in checks if not passed), None)
                outcomes.append(reason or "accepted")
                if reason is None:
                    sequence = command.sequence
            case _:
                assert_never(step.event)
    return tuple(outcomes)
