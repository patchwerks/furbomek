"""Map validated protocol observations into bounded tool results."""

from dataclasses import dataclass
from typing import Final, Literal

from furbomek_gateway.guard_models import (
    ActionName,
    GuardStopResult,
    MotorOffCheckResult,
    PoweredActionDecision,
    PoweredActionReason,
    PoweredActionResult,
)
from furbomek_gateway.guard_protocol import GuardReply, GuardResult, GuardState
from furbomek_gateway.guard_serial import StopExchange

_STOP_FAULT_CODE: Final = 4
type CheckDecision = Literal["completed", "refused", "unavailable"]
type CheckReason = Literal[
    "completed_without_physical_observation",
    "mode_not_qualified",
    "supply_gate_failed",
    "guard_not_boot",
    "protocol_rejected",
    "operation_timeout",
    "transport_failure",
    "cancelled",
]


@dataclass(frozen=True, slots=True)
class CheckOutcome:
    """Facts observed during a single check, not physical motion claims."""

    decision: CheckDecision
    reason: CheckReason
    supply: float | None = None
    active_accepted: bool = False
    busy_cleared: bool = False
    lease_lower_bound_ms: int | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class PoweredActionFacts:
    """Protocol facts collected by one powered action attempt."""

    action: ActionName
    decision: PoweredActionDecision
    reason: PoweredActionReason
    supply: float | None
    action_accepted: bool
    action_completed: bool
    disarm_acknowledged: bool
    lease_lower_bound_ms: int | None = None


def armed(reply: GuardReply) -> bool:
    """Accept only a healthy Armed acknowledgement."""
    return (
        reply.result is GuardResult.ACCEPTED
        and reply.state is GuardState.ARMED
        and reply.fault == 0
    )


def verified_stop(exchange: StopExchange | None) -> bool:
    """Verify the explicit terminal STOP fault, not any non-busy state."""
    if exchange is None or exchange.reply is None:
        return False
    reply = exchange.reply
    return (
        reply.result is GuardResult.ACCEPTED
        and reply.state is GuardState.FAULT
        and reply.fault == _STOP_FAULT_CODE
        and not reply.busy
    )


def stop_result(exchange: StopExchange | None) -> GuardStopResult:
    """Distinguish a successful local write from a robot acknowledgement."""
    verified = verified_stop(exchange)
    sent = exchange is not None and exchange.frame_sent
    return GuardStopResult(
        available=sent,
        stop_frame_sent=sent,
        fault_verified=verified,
        physical_reset_required=True if verified else None,
        error_code=None if sent else "transport_failure",
    )


def check_result(
    outcome: CheckOutcome, exchange: StopExchange | None
) -> MotorOffCheckResult:
    """Return observed check facts without inferring energized motion."""
    verified = verified_stop(exchange)
    sent = exchange is not None and exchange.frame_sent
    return MotorOffCheckResult(
        decision=outcome.decision,
        reason=outcome.reason,
        supply_voltage_volts=outcome.supply,
        active_accepted=outcome.active_accepted,
        busy_cleared=outcome.busy_cleared,
        stop_frame_sent=sent,
        fault_verified=verified,
        physical_reset_required=True if verified else None,
        lease_lower_bound_ms=outcome.lease_lower_bound_ms,
        available=sent,
    )


def state_name(
    state: GuardState,
) -> Literal["boot", "session", "arming", "armed", "disarmed", "fault"]:
    """Render the closed Guard state enum exhaustively."""
    match state:
        case GuardState.BOOT:
            return "boot"
        case GuardState.SESSION:
            return "session"
        case GuardState.ARMING:
            return "arming"
        case GuardState.ARMED:
            return "armed"
        case GuardState.DISARMED:
            return "disarmed"
        case GuardState.FAULT:
            return "fault"


def powered_action_result(
    facts: PoweredActionFacts,
    exchange: StopExchange | None,
    error_code: str | None = None,
) -> PoweredActionResult:
    """Build a factual powered-action result from protocol observations."""
    verified = verified_stop(exchange)
    sent = exchange is not None and exchange.frame_sent
    return PoweredActionResult(
        action=facts.action,
        decision=facts.decision,
        reason=facts.reason,
        supply_voltage_volts=facts.supply,
        action_accepted=facts.action_accepted,
        action_completed=facts.action_completed,
        disarm_acknowledged=facts.disarm_acknowledged,
        stop_frame_sent=sent,
        fault_verified=verified,
        physical_reset_required=(
            True if verified else False if facts.disarm_acknowledged else None
        ),
        available=sent or facts.decision == "completed",
        lease_lower_bound_ms=facts.lease_lower_bound_ms,
        error_code=error_code,
    )
