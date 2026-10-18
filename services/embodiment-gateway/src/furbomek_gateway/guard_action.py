"""Supervised powered semantic action lifecycle."""

import secrets
from dataclasses import dataclass, replace
from math import ceil

import anyio

from furbomek_gateway.guard_action_poll import (
    WIRE_ACTIONS,
    shielded_stop,
    wait_for_completion,
)
from furbomek_gateway.guard_models import (
    ActionName,
    GuardSettings,
    PoweredActionReason,
    PoweredActionResult,
)
from furbomek_gateway.guard_protocol import (
    GuardCommand,
    GuardResult,
    GuardState,
)
from furbomek_gateway.guard_results import (
    PoweredActionFacts,
    armed,
    powered_action_result,
)
from furbomek_gateway.guard_serial import (
    BeginAttempt,
    GuardSerialTransport,
    StopExchange,
)
from furbomek_gateway.guard_serial_errors import GuardSerialError, GuardSerialErrorCode

_SUPPLY_MIN_VOLTS = 6.5
_SUPPLY_MAX_VOLTS = 8.6


@dataclass(frozen=True, slots=True)
class ActionTransportContext:  # noqa: D101
    settings: GuardSettings
    transport: GuardSerialTransport
    control_lock: anyio.Lock
    operation_gate: anyio.Lock


@dataclass(frozen=True, slots=True)
class _ActiveAction:
    scope: anyio.CancelScope
    done: anyio.Event


@dataclass(slots=True)
class PoweredActionRunner:  # noqa: D101
    context: ActionTransportContext
    _active: _ActiveAction | None = None
    _attempt: BeginAttempt | None = None
    _in_flight_facts: PoweredActionFacts | None = None

    @property
    def is_active(self) -> bool:  # noqa: D102
        return self._active is not None

    def cancel_active(self) -> None:  # noqa: D102
        if (active := self._active) is not None:
            active.scope.cancel()

    async def wait_active_done(self) -> None:  # noqa: D102
        if (active := self._active) is not None:
            await active.done.wait()

    async def run(self, action: ActionName) -> PoweredActionResult:  # noqa: D102
        facts = PoweredActionFacts(
            action=action,
            decision="unavailable",
            reason="transport_failure",
            supply=None,
            action_accepted=False,
            action_completed=False,
            disarm_acknowledged=False,
        )
        exchange: StopExchange | None = None
        error_code: str | None = None

        with anyio.CancelScope() as scope:
            active = _ActiveAction(scope, anyio.Event())
            self._in_flight_facts = None
            async with self.context.control_lock:
                if self._active is not None:
                    return powered_action_result(
                        PoweredActionFacts(
                            action=action,
                            decision="refused",
                            reason="protocol_rejected",
                            supply=None,
                            action_accepted=False,
                            action_completed=False,
                            disarm_acknowledged=False,
                        ),
                        None,
                    )
                self._active = active
            try:
                async with self.context.operation_gate:
                    facts = await self._execute(action)
            except GuardSerialError as error:
                error_code = error.code.value
                base_facts = self._in_flight_facts or facts
                reason = (
                    "guard_not_ready"
                    if (self._attempt is None or not self._attempt.write_started)
                    and error.code
                    in (
                        GuardSerialErrorCode.PROTOCOL,
                        GuardSerialErrorCode.STALE_REPLY,
                    )
                    else "transport_failure"
                )
                facts = replace(base_facts, decision="unavailable", reason=reason)
            except anyio.get_cancelled_exc_class():
                facts = replace(
                    self._in_flight_facts or facts,
                    decision="unavailable",
                    reason="cancelled",
                )
                if not scope.cancel_called:
                    raise
            finally:
                with anyio.CancelScope(shield=True):
                    attempt_started = (
                        self._attempt is not None and self._attempt.write_started
                    )
                    if attempt_started and not facts.disarm_acknowledged:
                        exchange = await shielded_stop(self.context.transport)
                    async with self.context.control_lock:
                        if self._active is active:
                            self._active = None
                        active.done.set()
                    self._attempt = None
                    self._in_flight_facts = None
        return powered_action_result(
            facts,
            exchange,
            error_code,
        )

    async def _execute(self, action: ActionName) -> PoweredActionFacts:
        supply_reply = await self.context.transport.supply()
        supply = supply_reply.supply_voltage_volts
        if (
            supply_reply.result is not GuardResult.ACCEPTED
            or supply is None
            or not _SUPPLY_MIN_VOLTS <= supply <= _SUPPLY_MAX_VOLTS
        ):
            return PoweredActionFacts(
                action=action,
                decision="refused",
                reason="supply_gate_failed",
                supply=supply,
                action_accepted=False,
                action_completed=False,
                disarm_acknowledged=False,
            )
        self._in_flight_facts = PoweredActionFacts(
            action=action,
            decision="unavailable",
            reason="guard_not_ready",
            supply=supply,
            action_accepted=False,
            action_completed=False,
            disarm_acknowledged=False,
        )
        attempt = BeginAttempt()
        self._attempt = attempt
        begin = await self.context.transport.begin_state_aware(
            secrets.token_bytes(8), attempt
        )
        failure_reason: PoweredActionReason | None = None
        action_accepted = False
        action_completed = False
        disarm_acknowledged = False
        lease_lower_bound_ms: int | None = None
        if (
            begin.result is not GuardResult.ACCEPTED
            or begin.state is not GuardState.SESSION
        ):
            failure_reason = "guard_not_ready"
        else:
            arm = await self.context.transport.command(GuardCommand.ARM)
            if not armed(arm) or arm.busy:
                failure_reason = "guard_not_ready"
            else:
                execute = await self.context.transport.command(
                    GuardCommand.EXEC, action=WIRE_ACTIONS[action]
                )
                if (
                    execute.result is not GuardResult.ACCEPTED
                    or not armed(execute)
                    or not execute.busy
                ):
                    failure_reason = "protocol_rejected"
                else:
                    action_accepted = True
                    self._in_flight_facts = PoweredActionFacts(
                        action=action,
                        decision="unavailable",
                        reason="operation_timeout",
                        supply=supply,
                        action_accepted=True,
                        action_completed=False,
                        disarm_acknowledged=False,
                    )
                    poll = await wait_for_completion(
                        self.context.transport,
                        self.context.settings.action_timeout_ms / 1000,
                        ceil(self.context.settings.exchange_timeout_seconds * 1000)
                        + 30,
                    )
                    action_completed = poll.completed
                    lease_lower_bound_ms = poll.lease_lower_bound_ms
                    self._in_flight_facts = replace(
                        self._in_flight_facts,
                        lease_lower_bound_ms=lease_lower_bound_ms,
                    )
                    if not action_completed:
                        failure_reason = "operation_timeout"
                    else:
                        self._in_flight_facts = replace(
                            self._in_flight_facts,
                            action_completed=True,
                        )
                        disarm = await self.context.transport.command(
                            GuardCommand.DISARM
                        )
                        disarm_acknowledged = (
                            disarm.result is GuardResult.ACCEPTED
                            and disarm.state is GuardState.DISARMED
                            and disarm.fault == 0
                            and not disarm.busy
                        )
                        if disarm_acknowledged:
                            return PoweredActionFacts(
                                action=action,
                                decision="completed",
                                reason="completed_and_disarmed",
                                supply=supply,
                                action_accepted=True,
                                action_completed=True,
                                disarm_acknowledged=True,
                                lease_lower_bound_ms=lease_lower_bound_ms,
                            )
                        failure_reason = "disarm_rejected"
        return PoweredActionFacts(
            action=action,
            decision="unavailable",
            reason=failure_reason,
            supply=supply,
            action_accepted=action_accepted,
            action_completed=action_completed,
            disarm_acknowledged=disarm_acknowledged,
            lease_lower_bound_ms=lease_lower_bound_ms,
        )
