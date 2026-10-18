"""Bounded motor-off check lifecycle for the guarded adapter."""

import secrets
from dataclasses import dataclass
from math import ceil

import anyio

from furbomek_gateway.guard_action_poll import wait_for_completion
from furbomek_gateway.guard_models import GuardSettings, MotorOffCheckResult
from furbomek_gateway.guard_protocol import GuardCommand, GuardResult, GuardState
from furbomek_gateway.guard_results import (
    CheckDecision,
    CheckOutcome,
    CheckReason,
    armed,
    check_result,
)
from furbomek_gateway.guard_serial import (
    GuardSerialTransport,
    StopExchange,
)
from furbomek_gateway.guard_serial_errors import GuardSerialError, GuardSerialErrorCode

_SUPPLY_GATE_VOLTS = 3.0


@dataclass(frozen=True, slots=True)
class MotorOffContext:
    """Shared transport and locks for the motor-off lifecycle."""

    settings: GuardSettings
    transport: GuardSerialTransport
    control_lock: anyio.Lock
    operation_gate: anyio.Lock


@dataclass(slots=True)
class MotorOffRunner:
    """Run the existing bounded motor-off check without changing its API."""

    context: MotorOffContext
    _active: anyio.CancelScope | None = None
    _done: anyio.Event | None = None

    @property
    def is_active(self) -> bool:
        """Report whether this runner currently owns a check."""
        return self._active is not None

    def cancel_active(self) -> None:
        """Cancel the owned check without touching the transport."""
        if self._active is not None:
            self._active.cancel()

    async def wait_active_done(self) -> None:
        """Wait for shielded check cleanup to finish."""
        if self._done is not None:
            await self._done.wait()

    async def run(self) -> MotorOffCheckResult:
        """Run one bounded motor-off protocol check."""
        supply: float | None = None
        active_accepted = False
        busy_cleared = False
        reason: CheckReason = "cancelled"
        decision: CheckDecision = "unavailable"
        exchange: StopExchange | None = None
        lease_lower_bound_ms: int | None = None
        with anyio.CancelScope() as scope:
            done = anyio.Event()
            async with self.context.control_lock:
                if self._active is not None:
                    return check_result(
                        CheckOutcome("refused", "protocol_rejected"), None
                    )
                self._active = scope
                self._done = done
            try:
                async with self.context.operation_gate:
                    supply_reply = await self.context.transport.supply()
                    supply = supply_reply.supply_voltage_volts
                    if (
                        supply_reply.result is not GuardResult.ACCEPTED
                        or supply is None
                        or not 0 <= supply < _SUPPLY_GATE_VOLTS
                    ):
                        reason, decision = "supply_gate_failed", "refused"
                    else:
                        status = await self.context.transport.command(
                            GuardCommand.STATUS
                        )
                        if (
                            status.result is not GuardResult.ACCEPTED
                            or status.state is not GuardState.BOOT
                        ):
                            reason, decision = "guard_not_boot", "refused"
                        else:
                            await self._begin_arm_execute()
                            active_accepted = True
                            poll = await wait_for_completion(
                                self.context.transport,
                                self.context.settings.active_check_timeout_ms / 1000,
                                ceil(
                                    self.context.settings.exchange_timeout_seconds
                                    * 1000
                                )
                                + 30,
                            )
                            busy_cleared = poll.completed
                            lease_lower_bound_ms = poll.lease_lower_bound_ms
                            reason = (
                                "completed_without_physical_observation"
                                if busy_cleared
                                else "operation_timeout"
                            )
                            decision = "completed" if busy_cleared else "unavailable"
            except GuardSerialError:
                reason = "transport_failure"
            except anyio.get_cancelled_exc_class():
                reason, decision = "cancelled", "unavailable"
                if not scope.cancel_called:
                    raise
            finally:
                with anyio.CancelScope(shield=True):
                    exchange = await self._shielded_stop()
                    async with self.context.control_lock:
                        self._active = None
                        self._done = None
                        done.set()
        await anyio.lowlevel.checkpoint()
        return check_result(
            CheckOutcome(
                decision,
                reason,
                supply,
                active_accepted,
                busy_cleared,
                lease_lower_bound_ms,
            ),
            exchange,
        )

    async def _begin_arm_execute(self) -> None:
        begin = await self.context.transport.begin(secrets.token_bytes(8))
        if (
            begin.result is not GuardResult.ACCEPTED
            or begin.state is not GuardState.SESSION
        ):
            raise GuardSerialError(GuardSerialErrorCode.PROTOCOL)
        arm = await self.context.transport.command(GuardCommand.ARM)
        if not armed(arm) or arm.busy:
            raise GuardSerialError(GuardSerialErrorCode.PROTOCOL)
        execute = await self.context.transport.command(GuardCommand.EXEC, action=0)
        if not armed(execute) or not execute.busy:
            raise GuardSerialError(GuardSerialErrorCode.PROTOCOL)

    async def _shielded_stop(self) -> StopExchange | None:
        with anyio.CancelScope(shield=True):
            try:
                return await self.context.transport.stop()
            except GuardSerialError:
                return None
