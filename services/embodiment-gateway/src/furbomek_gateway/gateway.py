"""Typed service operations for read-only stock access and policy denial."""

from furbomek_gateway.models import (
    CapabilitiesResult,
    MotionRequest,
    MotionRequestResult,
    ResultStatus,
    RobotStateResult,
    SupplyVoltageResult,
)
from furbomek_gateway.transport import StockTcpTransport, StockTransportError


class GatewayService:
    """Typed service boundary for stock reads and blocked motion requests."""

    def __init__(self, transport: StockTcpTransport) -> None:
        """Create a service around one serialized stock transport."""
        self._transport: StockTcpTransport = transport

    async def get_state(self) -> RobotStateResult:
        """Return stock echo connectivity without inferring actuator state."""
        try:
            await self._transport.get_state()
        except StockTransportError as error:
            return RobotStateResult(
                status=ResultStatus.UNAVAILABLE,
                connected=False,
                stock_echo_validated=False,
                motor_power_known=False,
                joint_positions_known=False,
                stop_capability_qualified=False,
                error_code=error.error_code,
            )
        return RobotStateResult(
            status=ResultStatus.CONNECTED,
            connected=True,
            stock_echo_validated=True,
            motor_power_known=False,
            joint_positions_known=False,
            stop_capability_qualified=False,
        )

    async def get_supply_voltage(self) -> SupplyVoltageResult:
        """Return the controller-reported voltage with its safety limits."""
        try:
            reading = await self._transport.get_supply_voltage()
        except StockTransportError as error:
            return SupplyVoltageResult(
                status=ResultStatus.UNAVAILABLE,
                connected=False,
                error_code=error.error_code,
            )
        return SupplyVoltageResult(
            status=ResultStatus.CONNECTED,
            connected=True,
            controller_reported_voltage_volts=reading.volts,
            interpretation=(
                "controller_reported_not_calibrated_or_independent_power_safety"
            ),
        )

    def get_capabilities(self) -> CapabilitiesResult:
        """Return factual stock protocol and current safety qualification flags."""
        return CapabilitiesResult(
            stock_per_leg_protocol_available=True,
            stock_gait_protocol_available=True,
            preemptive_stop_qualified=False,
            local_ttl_watchdog_qualified=False,
            current_backend_readonly=True,
            actuator_commands_targeted=False,
            unresolved_faults=("rear_right_leg",),
        )

    def request_motion(self, request: MotionRequest) -> MotionRequestResult:
        """Reject motion before transport access while local safety is unqualified."""
        _ = request
        return MotionRequestResult(
            decision="rejected",
            reason="local_safety_unqualified",
            sent=False,
            network_accessed=False,
        )
