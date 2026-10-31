"""FastMCP registration for the gateway service."""

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from furbomek_gateway.gateway import GatewayService
from furbomek_gateway.models import (
    CapabilitiesResult,
    GatewaySettings,
    MotionRequest,
    MotionRequestResult,
    RobotStateResult,
    SupplyVoltageResult,
)
from furbomek_gateway.transport import StockTcpTransport

_READ_ONLY_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)


def create_server(settings: GatewaySettings) -> FastMCP:
    """Build the MCP server with endpoint settings outside tool arguments."""
    service = GatewayService(StockTcpTransport(settings))
    server = FastMCP(
        name="furbomek-embodiment-gateway",
        instructions=(
            "Stock Freenove reads only. Motion requests are policy-evaluated and "
            "rejected until robot-local safety is qualified."
        ),
    )

    @server.tool(
        name="robot_get_state",
        description=(
            "Validate the stock echo over TCP. This does not infer motor power, "
            "joint positions, or STOP capability."
        ),
        annotations=_READ_ONLY_ANNOTATIONS,
        structured_output=True,
    )
    async def robot_get_state() -> RobotStateResult:
        """Validate the stock echo without inferring actuator state."""
        return await service.get_state()

    @server.tool(
        name="robot_get_supply_voltage",
        description=(
            "Read the stock controller-reported voltage; it is not calibrated "
            "or independent power safety evidence."
        ),
        annotations=_READ_ONLY_ANNOTATIONS,
        structured_output=True,
    )
    async def robot_get_supply_voltage() -> SupplyVoltageResult:
        """Read the controller-reported supply encoding."""
        return await service.get_supply_voltage()

    @server.tool(
        name="robot_get_capabilities",
        description=(
            "Report factual stock protocol availability and the current read-only "
            "safety boundary."
        ),
        annotations=_READ_ONLY_ANNOTATIONS,
        structured_output=True,
    )
    async def robot_get_capabilities() -> CapabilitiesResult:
        """Report stock protocol facts and current qualification flags."""
        return service.get_capabilities()

    @server.tool(
        name="robot_request_motion",
        description=(
            "Evaluate a bounded semantic motion request. It is always rejected "
            "before socket access while robot-local TTL/watchdog/preemptive STOP "
            "is unqualified; this tool does not execute motion."
        ),
        annotations=_READ_ONLY_ANNOTATIONS,
        structured_output=True,
    )
    def robot_request_motion(request: MotionRequest) -> MotionRequestResult:
        """Evaluate motion policy without building or sending a stock packet."""
        return service.request_motion(request)

    return server
