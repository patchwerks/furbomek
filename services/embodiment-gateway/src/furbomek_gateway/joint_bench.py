"""Local joint probe runner and angle calculation for the bench diagnostic."""

import math
import secrets
from dataclasses import dataclass
from typing import Annotated, Final, Literal, Self, override

from pydantic import BaseModel, Field, model_validator

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
_WIDE_PROBE_DEGREES: Final = 36


class JointProbe(BaseModel, frozen=True, extra="forbid"):
    """One finite diagnostic address, outside the MCP action model."""

    leg: Annotated[int, Field(ge=1, le=6, strict=True)]
    axis: Literal["yaw", "femur", "knee"]
    direction: Literal["negative", "positive"]
    degrees: Literal[6, 18, 30, 36]
    speed: Literal["baseline", "fast"] = "baseline"

    @model_validator(mode="after")
    def validate_band(self) -> Self:
        """Reject axis and speed combinations outside the bench profiles."""
        if (self.degrees == _WIDE_PROBE_DEGREES and self.axis == "femur") or (
            self.degrees != _WIDE_PROBE_DEGREES and self.speed == "fast"
        ):
            raise JointProbeBandError
        return self

    @property
    def code(self) -> int:
        """Map the joint and band to the bench firmware's finite code."""
        if self.degrees == _WIDE_PROBE_DEGREES:
            return (
                119
                + (self.leg - 1) * 8
                + (4 if self.axis == "knee" else 0)
                + (2 if self.direction == "positive" else 0)
                + int(self.speed == "fast")
            )
        axis = ("yaw", "femur", "knee").index(self.axis)
        direction = 3 if self.direction == "positive" else 0
        return (
            11
            + ((self.leg - 1) * 3 + axis) * 6
            + direction
            + (6, 18, 30).index(self.degrees)
        )


class JointProbeBandError(ValueError):
    """The requested step size or axis is outside the diagnostic band."""


type BenchHeight = Literal["low", "middle", "high"]


class TableMotion(BaseModel, frozen=True, extra="forbid"):
    """Select one fixed table action and one of its measured step sizes."""

    action: Literal["hold", "walk", "walk_continuous"]
    height: BenchHeight
    speed: Literal["baseline", "fast"]

    @property
    def code(self) -> int:
        """Translate only the twelve fixed table actions."""
        return (
            170
            + 6 * ("hold", "walk", "walk_continuous").index(self.action)
            + 2 * ("low", "middle", "high").index(self.height)
            + int(self.speed == "fast")
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
    transport: GuardSerialTransport,
    code: int | None,
    *,
    arm_only: bool,
    timeout_seconds: float = 2.5,
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
            if code is None:
                launch = await transport.command(GuardCommand.EXEC, action=0)
            else:
                launch = await transport.execute_bench_action(code)
            _require(launch, GuardState.ARMED, busy=True)
            poll = await wait_for_completion(transport, timeout_seconds, 230)
            if not poll.completed:
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
    return await _run(transport, probe.code, arm_only=False)


async def run_height(transport: GuardSerialTransport, height: BenchHeight) -> bool:
    """Apply a supported height preset through the guarded bench session."""
    code = 167 + ("low", "middle", "high").index(height)
    return await _run(transport, code, arm_only=False)


async def run_table(transport: GuardSerialTransport, motion: TableMotion) -> bool:
    """Run a bounded loaded hold or forward step for camera evaluation."""
    timeout = 2.5 if motion.action == "walk" else 6.0
    return await _run(transport, motion.code, arm_only=False, timeout_seconds=timeout)


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
