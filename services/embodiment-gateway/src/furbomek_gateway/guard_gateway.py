"""Safety policy for the separate guarded UART MCP server."""

from typing import final

import anyio

from furbomek_gateway.guard_action import (
    ActionTransportContext,
    PoweredActionRunner,
)
from furbomek_gateway.guard_models import (
    ActionName,
    GuardCapabilitiesResult,
    GuardSettings,
    GuardStateResult,
    GuardStopResult,
    GuardSupplyVoltageResult,
    MotorOffCheckResult,
    PoweredActionResult,
)
from furbomek_gateway.guard_motor_off import MotorOffContext, MotorOffRunner
from furbomek_gateway.guard_protocol import GuardCommand, GuardResult, GuardState
from furbomek_gateway.guard_results import (
    PoweredActionFacts,
    powered_action_result,
    state_name,
    stop_result,
)
from furbomek_gateway.guard_serial import (
    GuardSerialTransport,
    StopExchange,
)
from furbomek_gateway.guard_serial_errors import GuardSerialError, GuardSerialErrorCode


@final
class GuardService:
    """One bounded policy facade around the persistent guarded transport."""

    def __init__(self, settings: GuardSettings) -> None:
        """Create unopened service state for the MCP lifespan."""
        self._settings = settings
        self._transport: GuardSerialTransport | None = None
        self._control_lock = anyio.Lock()
        self._operation_gate = anyio.Lock()
        self._motor_off: MotorOffRunner | None = None
        self._powered: PoweredActionRunner | None = None

    async def open(self) -> None:
        """Open the configured bridge once for this server process."""
        self._transport = await GuardSerialTransport.open(self._settings)
        self._motor_off = MotorOffRunner(
            MotorOffContext(
                self._settings,
                self._transport,
                self._control_lock,
                self._operation_gate,
            )
        )
        self._powered = PoweredActionRunner(
            ActionTransportContext(
                self._settings,
                self._transport,
                self._control_lock,
                self._operation_gate,
            )
        )

    async def aclose(self) -> None:
        """Close the bridge after shielded cleanup of an active operation."""
        with anyio.CancelScope(shield=True):
            async with self._control_lock:
                motor_active = self._motor_off is not None and self._motor_off.is_active
                powered_active = self._powered is not None and self._powered.is_active
                if motor_active and self._motor_off is not None:
                    self._motor_off.cancel_active()
                if powered_active and self._powered is not None:
                    self._powered.cancel_active()
            if motor_active:
                _ = await self._shielded_stop()
                if self._motor_off is not None:
                    with anyio.move_on_after(1):
                        await self._motor_off.wait_active_done()
            if powered_active:
                _ = await self._shielded_stop()
                if self._powered is not None:
                    with anyio.move_on_after(1):
                        await self._powered.wait_active_done()
            if self._transport is not None:
                await self._transport.aclose()
                self._transport = None
                self._motor_off = None
                self._powered = None

    async def get_state(self) -> GuardStateResult:
        """Query Guard STATUS without arming or inferring physical motor state."""
        try:
            async with self._operation_gate:
                transport = self._transport_or_error()
                reply = (
                    await transport.status_sync()
                    if self._settings.mode == "supervised_powered_bench"
                    else await transport.command(GuardCommand.STATUS)
                )
        except GuardSerialError as error:
            return GuardStateResult(
                available=False,
                guard_state=None,
                busy=None,
                fault_code=None,
                physical_reset_required=None,
                error_code=error.code.value,
            )
        return GuardStateResult(
            available=True,
            guard_state=state_name(reply.state),
            busy=reply.busy,
            fault_code=reply.fault,
            physical_reset_required=reply.state is GuardState.FAULT,
        )

    async def get_supply_voltage(self) -> GuardSupplyVoltageResult:
        """Query Guard supply without starting a session or renewing a lease."""
        try:
            async with self._operation_gate:
                reply = await self._transport_or_error().supply()
        except GuardSerialError as error:
            return GuardSupplyVoltageResult(
                available=False,
                supply_voltage_volts=None,
                interpretation="not_independent_motor_power_proof",
                error_code=error.code.value,
            )
        if (
            reply.result is not GuardResult.ACCEPTED
            or reply.supply_voltage_volts is None
        ):
            return GuardSupplyVoltageResult(
                available=False,
                supply_voltage_volts=None,
                interpretation="not_independent_motor_power_proof",
                error_code="protocol_refused",
            )
        return GuardSupplyVoltageResult(
            available=True,
            supply_voltage_volts=reply.supply_voltage_volts,
            interpretation="not_independent_motor_power_proof",
        )

    def get_capabilities(self) -> GuardCapabilitiesResult:
        """Return the configured mode and its closed action boundary."""
        return GuardCapabilitiesResult(
            available=self._transport is not None,
            one_bounded_active_check_available=self._settings.mode == "motor_off_bench",
            powered_semantic_action_available=(
                self._settings.mode == "supervised_powered_bench"
                and self._settings.operator_profile
                == "operator_present_supported_chassis"
            ),
            configured_mode=self._settings.mode,
            operator_profile=self._settings.operator_profile,
            qualified_actions=self._settings.qualified_actions,
        )

    async def stop(self) -> GuardStopResult:
        """Cancel active work, then send the real terminal STOP immediately."""
        async with self._control_lock:
            if self._motor_off is not None:
                self._motor_off.cancel_active()
            if self._powered is not None:
                self._powered.cancel_active()
        return stop_result(await self._shielded_stop())

    async def perform_action(self, action: ActionName) -> PoweredActionResult:
        """Run one explicitly qualified semantic action in powered mode."""
        if self._settings.mode != "supervised_powered_bench":
            return powered_action_result(
                PoweredActionFacts(
                    action=action,
                    decision="refused",
                    reason="mode_not_qualified",
                    supply=None,
                    action_accepted=False,
                    action_completed=False,
                    disarm_acknowledged=False,
                ),
                None,
            )
        if action not in self._settings.qualified_actions:
            return powered_action_result(
                PoweredActionFacts(
                    action=action,
                    decision="refused",
                    reason="action_not_qualified",
                    supply=None,
                    action_accepted=False,
                    action_completed=False,
                    disarm_acknowledged=False,
                ),
                None,
            )
        if self._powered is None:
            return powered_action_result(
                PoweredActionFacts(
                    action=action,
                    decision="unavailable",
                    reason="transport_failure",
                    supply=None,
                    action_accepted=False,
                    action_completed=False,
                    disarm_acknowledged=False,
                ),
                None,
                GuardSerialErrorCode.CONNECTION.value,
            )
        return await self._powered.run(action)

    async def run_motor_off_check(self) -> MotorOffCheckResult:
        """Run the legacy bounded Active check only in motor-off mode."""
        if self._settings.mode != "motor_off_bench":
            return MotorOffCheckResult(
                decision="refused",
                reason="mode_not_qualified",
                supply_voltage_volts=None,
                active_accepted=False,
                busy_cleared=False,
                stop_frame_sent=False,
                fault_verified=False,
                physical_reset_required=None,
                available=self._transport is not None,
            )
        if self._motor_off is None:
            raise GuardSerialError(GuardSerialErrorCode.CONNECTION)
        return await self._motor_off.run()

    async def _shielded_stop(self) -> StopExchange | None:
        with anyio.CancelScope(shield=True):
            try:
                return await self._transport_or_error().stop()
            except GuardSerialError:
                return None

    def _transport_or_error(self) -> GuardSerialTransport:
        if self._transport is None:
            raise GuardSerialError(GuardSerialErrorCode.CONNECTION)
        return self._transport
