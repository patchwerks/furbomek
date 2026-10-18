"""Heartbeat and status polling for one bounded powered action."""

from dataclasses import dataclass
from math import ceil

import anyio

from furbomek_gateway.guard_models import ActionName
from furbomek_gateway.guard_protocol import (
    GuardAction,
    GuardCommand,
    GuardReply,
    GuardResult,
    GuardState,
)
from furbomek_gateway.guard_serial import (
    GuardSerialTransport,
    StopExchange,
)
from furbomek_gateway.guard_serial_errors import GuardSerialError

WIRE_ACTIONS: dict[ActionName, GuardAction] = {
    "active": GuardAction.ACTIVE,
    "sleep": GuardAction.SLEEP,
    "forward": GuardAction.FORWARD,
    "backward": GuardAction.BACKWARD,
    "left": GuardAction.LEFT,
    "right": GuardAction.RIGHT,
    "turn_left": GuardAction.TURN_LEFT,
    "turn_right": GuardAction.TURN_RIGHT,
}


def armed_query(reply: GuardReply) -> bool:
    """Accept only healthy Armed ACK or validated query replay."""
    return (
        reply.result in (GuardResult.ACCEPTED, GuardResult.QUERY_REPLAY)
        and reply.state is GuardState.ARMED
        and reply.fault == 0
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class PollResult:
    """One KEEPALIVE observation and its conservative lease bound."""

    completed: bool
    lease_lower_bound_ms: int | None


async def wait_for_completion(
    transport: GuardSerialTransport, timeout_seconds: float, minimum_lease_ms: int
) -> PollResult:
    """Require healthy Armed status and busy=false before the deadline."""
    try:
        with anyio.fail_after(timeout_seconds):
            while True:
                cycle_started = anyio.current_time()
                heartbeat = await transport.command(GuardCommand.KEEPALIVE)
                if not armed_query(heartbeat):
                    return PollResult(
                        completed=False,
                        lease_lower_bound_ms=heartbeat.lease_lower_bound_ms,
                    )
                lease_lower_bound_ms = heartbeat.lease_lower_bound_ms
                planned_sleep = max(0, cycle_started + 0.1 - anyio.current_time())
                required_lease_ms = minimum_lease_ms + (
                    ceil(planned_sleep * 1000) if heartbeat.busy else 0
                )
                if (
                    lease_lower_bound_ms is None
                    or lease_lower_bound_ms < required_lease_ms
                ):
                    return PollResult(
                        completed=False,
                        lease_lower_bound_ms=lease_lower_bound_ms,
                    )
                if not heartbeat.busy:
                    return PollResult(
                        completed=True,
                        lease_lower_bound_ms=lease_lower_bound_ms,
                    )
                await anyio.sleep(planned_sleep)
    except TimeoutError:
        return PollResult(completed=False, lease_lower_bound_ms=None)


async def shielded_stop(transport: GuardSerialTransport) -> StopExchange | None:
    """Deliver raw STOP through a cancellation shield."""
    with anyio.CancelScope(shield=True):
        try:
            return await transport.stop()
        except GuardSerialError:
            return None
