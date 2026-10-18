"""Independent FastMCP registration for the fixed motor-off Guard adapter."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from furbomek_gateway.guard_gateway import GuardService
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

_READ_ONLY = ToolAnnotations(
    readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False
)
_STOP = ToolAnnotations(
    readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False
)
_CHECK = ToolAnnotations(
    readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False
)
_ACTION = ToolAnnotations(
    readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=False
)


def create_guard_server(settings: GuardSettings) -> FastMCP:
    """Build a separate stdio server with one lifespan-owned serial port."""
    service = GuardService(settings)

    @asynccontextmanager
    async def lifespan(_: FastMCP) -> AsyncGenerator[None]:
        await service.open()
        try:
            yield
        finally:
            await service.aclose()

    server = FastMCP(
        name="furbomek-guard",
        instructions=(
            f"Guarded robot control in operator-configured {settings.mode} mode. "
            "Read capabilities for the qualified action allowlist. Normal successful "
            "actions DISARM safely and may be repeated without reset. Emergency "
            "STOP and faults remain latched until deliberate physical reset; no "
            "tool clears faults or resets the controller. A trusted host maintenance "
            "agent can deliberately reset the robot over its existing USB DTR link "
            "after recovery is authorized and the user freshly confirms POWER OFF. "
            "Delegate that recovery rather than asking the user to find RESET; ask "
            "for physical reset only if USB recovery is unavailable or unsafe. "
            "Never automatically reset, clear a fault, or resume motion. See "
            "docs/operations/hermes-robot.md for the maintenance boundary. "
            "Protocol results do not "
            "independently prove motor power, physical motion or mechanical health."
        ),
        lifespan=lifespan,
    )

    @server.tool(name="robot_get_state", annotations=_READ_ONLY, structured_output=True)
    async def robot_get_state() -> GuardStateResult:
        """Read Guard state without arming, resetting, or inferring motor power."""
        return await service.get_state()

    @server.tool(
        name="robot_get_supply_voltage", annotations=_READ_ONLY, structured_output=True
    )
    async def robot_get_supply_voltage() -> GuardSupplyVoltageResult:
        """Read the Guard supply response; it is not independent power proof."""
        return await service.get_supply_voltage()

    @server.tool(
        name="robot_get_capabilities", annotations=_READ_ONLY, structured_output=True
    )
    def robot_get_capabilities() -> GuardCapabilitiesResult:
        """Report configured mode, qualified actions and untested reset behavior."""
        return service.get_capabilities()

    @server.tool(name="robot_stop", annotations=_STOP, structured_output=True)
    async def robot_stop() -> GuardStopResult:
        """Send the firmware-defined terminal raw STOP without a reset path."""
        return await service.stop()

    if settings.mode == "motor_off_bench":

        @server.tool(
            name="robot_run_motor_off_check", annotations=_CHECK, structured_output=True
        )
        async def robot_run_motor_off_check() -> MotorOffCheckResult:
            """Run one bounded Active check only after the conservative supply gate."""
            return await service.run_motor_off_check()

    @server.tool(
        name="robot_perform_action", annotations=_ACTION, structured_output=True
    )
    async def robot_perform_action(action: ActionName) -> PoweredActionResult:
        """Run one qualified action; normal completion disarms without a reset."""
        return await service.perform_action(action)

    return server
