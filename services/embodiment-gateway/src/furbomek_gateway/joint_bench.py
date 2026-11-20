"""Local joint probe runner and angle calculation for the bench diagnostic."""

import math
import secrets
from dataclasses import dataclass
from typing import Annotated, Final, Literal, override

from pydantic import BaseModel, Field

from furbomek_gateway.guard_action_poll import shielded_stop, wait_for_completion
from furbomek_gateway.guard_protocol import (
    GuardCommand,
    GuardReply,
    GuardResult,
    GuardState,
)
from furbomek_gateway.guard_serial import BeginAttempt, GuardSerialTransport

_MIN_VOLTAGE: Final = 6.5
_MAX_VOLTAGE: Final = 8.6
_MIN_LINK_LENGTH: Final = 1e-6
_MIN_PROJECTIVE_SCALE: Final = 1e-9


class JointProbe(BaseModel, frozen=True, extra="forbid"):
    """One finite diagnostic address, outside the MCP action model."""

    leg: Annotated[int, Field(ge=1, le=6, strict=True)]
    axis: Literal["yaw", "femur", "knee"]
    direction: Literal["negative", "positive"]
    degrees: Literal[6, 18, 30]

    @property
    def code(self) -> int:
        """Map the joint and band to the bench firmware's finite code."""
        axis = ("yaw", "femur", "knee").index(self.axis)
        direction = 3 if self.direction == "positive" else 0
        return (
            11
            + ((self.leg - 1) * 3 + axis) * 6
            + direction
            + (6, 18, 30).index(self.degrees)
        )


@dataclass(frozen=True, slots=True)
class JointProbeRejectedError(ValueError):
    """An acknowledgement did not satisfy the local probe lifecycle."""

    reply: GuardReply
    expected: GuardState

    @override
    def __str__(self) -> str:
        return (
            f"{self.reply.opcode.name} expected {self.expected.name}, "
            f"got {self.reply.result.name}/{self.reply.state.name} "
            f"(busy={self.reply.busy}, fault={self.reply.fault})"
        )


def _require(reply: GuardReply, status: GuardState, *, busy: bool = False) -> None:
    if (
        reply.result is not GuardResult.ACCEPTED
        or reply.state is not status
        or reply.busy is not busy
        or reply.fault
    ):
        raise JointProbeRejectedError(reply, status)


async def _run(
    transport: GuardSerialTransport, probe: JointProbe | None, *, arm_only: bool
) -> bool:
    supply = await transport.supply()
    voltage = supply.supply_voltage_volts
    if (
        supply.result is not GuardResult.ACCEPTED
        or voltage is None
        or not _MIN_VOLTAGE <= voltage <= _MAX_VOLTAGE
    ):
        return False
    attempt = BeginAttempt()
    disarmed = False
    try:
        session = await transport.begin_state_aware(
            secrets.token_bytes(8), attempt, require_disarmed=not arm_only
        )
        _require(session, GuardState.SESSION)
        _require(await transport.command(GuardCommand.ARM), GuardState.ARMED)
        if not arm_only:
            if probe is None:
                launch = await transport.command(GuardCommand.EXEC, action=0)
            else:
                launch = await transport.execute_joint_probe(probe.code)
            _require(launch, GuardState.ARMED, busy=True)
            if not (await wait_for_completion(transport, 2.5, 230)).completed:
                return False
        _require(await transport.command(GuardCommand.DISARM), GuardState.DISARMED)
        disarmed = True
    finally:
        if attempt.write_started and not disarmed:
            _ = await shielded_stop(transport)
    return disarmed


async def arm_only_check(transport: GuardSerialTransport) -> bool:
    """Verify the powered link with ARM and DISARM and no motion."""
    return await _run(transport, None, arm_only=True)


async def reference_stance(transport: GuardSerialTransport) -> bool:
    """Establish Active following a successful ARM-only check."""
    return await _run(transport, None, arm_only=False)


async def run_probe(transport: GuardSerialTransport, probe: JointProbe) -> bool:
    """Run one camera-observed probe on the prepared local link."""
    return await _run(transport, probe, arm_only=False)


type Point = tuple[float, float]
type MarkerSet = tuple[Point, Point, Point]
type PlaneMap = tuple[float, float, float, float, float, float, float, float, float]


class JointAngleError(ValueError):
    """Camera markers do not define two observable joint links."""


def signed_angle(proximal: Point, hinge: Point, distal: Point) -> float:
    """Measure the signed angle between two links in a rectified joint plane."""
    ax, ay = proximal[0] - hinge[0], proximal[1] - hinge[1]
    bx, by = distal[0] - hinge[0], distal[1] - hinge[1]
    ax, ay = -ax, -ay
    if not all(math.isfinite(v) for v in (ax, ay, bx, by)):
        raise JointAngleError
    if math.hypot(ax, ay) < _MIN_LINK_LENGTH or math.hypot(bx, by) < _MIN_LINK_LENGTH:
        raise JointAngleError
    return math.degrees(math.atan2(ax * by - ay * bx, ax * bx + ay * by))


def _project(point: Point, plane: PlaneMap) -> Point:
    x, y = point
    a, b, c, d, e, f, g, h, i = plane
    scale = g * x + h * y + i
    if not math.isfinite(scale) or abs(scale) < _MIN_PROJECTIVE_SCALE:
        raise JointAngleError
    return ((a * x + b * y + c) / scale, (d * x + e * y + f) / scale)


def observed_travel(reference: MarkerSet, sample: MarkerSet, plane: PlaneMap) -> float:
    """Compare marked link angles after rectifying pixels to the joint plane."""
    before = signed_angle(*(_project(point, plane) for point in reference))
    after = signed_angle(*(_project(point, plane) for point in sample))
    return (after - before + 180.0) % 360.0 - 180.0
