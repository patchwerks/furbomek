"""Profile-scoped MCP client for the reverse SSH socket on Brodex."""

from pathlib import Path

from mcp.server.fastmcp import FastMCP

from furbomek_gateway.edge_protocol import (
    EdgeReply,
    KinectCommand,
    KinectRequest,
    ObsCommand,
    ObsRequest,
    RobotRequest,
    exchange,
    unix_ms,
)
from furbomek_gateway.guard_models import ActionName


def create_edge_client(socket_path: Path) -> FastMCP:
    """Expose semantic tools over the Unix socket configured by the operator."""
    server = FastMCP(
        name="furbomek-mac-edge",
        instructions=(
            "Use camera and OBS only in the dedicated local test scene. "
            "Robot motion requires a fresh locally authorized, operator-present "
            "supported bench window. Never retry an uncertain motion result or "
            "attempt to bypass a local refusal."
        ),
    )

    @server.tool(structured_output=True)
    async def robot_get_state() -> EdgeReply:
        """Read the Mac's guarded robot state when locally admitted."""
        return await exchange(
            socket_path, RobotRequest(command="state", issued_ms=unix_ms())
        )

    @server.tool(structured_output=True)
    async def robot_get_supply_voltage() -> EdgeReply:
        """Read reported guard supply without arming or treating it as power proof."""
        return await exchange(
            socket_path, RobotRequest(command="voltage", issued_ms=unix_ms())
        )

    @server.tool(structured_output=True)
    async def robot_get_capabilities() -> EdgeReply:
        """Report the local bench admission state and configured action limits."""
        return await exchange(
            socket_path, RobotRequest(command="capabilities", issued_ms=unix_ms())
        )

    @server.tool(structured_output=True)
    async def robot_perform_action(action: ActionName) -> EdgeReply:
        """Request one bounded action during the locally enabled bench window."""
        return await exchange(
            socket_path, RobotRequest(command=action, issued_ms=unix_ms())
        )

    @server.tool(structured_output=True)
    async def robot_stop() -> EdgeReply:
        """Request the existing terminal STOP when the bridge is available."""
        return await exchange(
            socket_path, RobotRequest(command="stop", issued_ms=unix_ms())
        )

    @server.tool(structured_output=True)
    async def kinect_control(action: KinectCommand) -> EdgeReply:
        """Start or stop Kinect media, read health, or choose an approved Godot view."""
        return await exchange(
            socket_path, KinectRequest(command=action, issued_ms=unix_ms())
        )

    @server.tool(structured_output=True)
    async def obs_control(action: ObsCommand) -> EdgeReply:
        """Control the dedicated OBS profile. Twitch output is bandwidth-test only."""
        return await exchange(
            socket_path, ObsRequest(command=action, issued_ms=unix_ms())
        )

    return server
