import sys
from ipaddress import IPv4Address
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from furbomek_gateway.models import GatewaySettings
from tests.support import wire_server

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.anyio
async def test_stdio_lists_and_calls_readonly_tools(tmp_path: Path) -> None:
    responses = {
        b"\x80\x00\x81": b"\x80\x01\x81",
        b"\x80\x0a\x81": b"\x80\x0b\x01\x02\x81",
    }
    settings = GatewaySettings(
        host=IPv4Address("127.0.0.1"),
        port=1,
        timeout_seconds=0.5,
    )

    async with wire_server(
        lambda request: responses.get(request, b"\x80\x02\x81")
    ) as fixture:
        settings = settings.model_copy(update={"port": fixture.port})
        settings_path = tmp_path / "settings.json"
        _ = settings_path.write_text(settings.model_dump_json(), encoding="utf-8")
        parameters = StdioServerParameters(
            command=sys.executable,
            args=[
                "-m",
                "furbomek_gateway",
                "serve",
                "--settings",
                str(settings_path),
            ],
            cwd=PROJECT_ROOT,
        )

        async with (
            stdio_client(parameters) as (read_stream, write_stream),
            ClientSession(read_stream, write_stream) as session,
        ):
            _ = await session.initialize()
            listed = await session.list_tools()
            names = tuple(sorted(tool.name for tool in listed.tools))

            state = await session.call_tool("robot_get_state")
            supply = await session.call_tool("robot_get_supply_voltage")

            assert names == (
                "robot_get_capabilities",
                "robot_get_state",
                "robot_get_supply_voltage",
                "robot_request_motion",
            )
            annotations = [tool.annotations for tool in listed.tools]
            assert all(annotation is not None for annotation in annotations)
            assert all(
                annotation.readOnlyHint is True
                for annotation in annotations
                if annotation is not None
            )
            assert state.isError is False
            assert state.structuredContent == {
                "status": "connected",
                "connected": True,
                "stock_echo_validated": True,
                "motor_power_known": False,
                "joint_positions_known": False,
                "stop_capability_qualified": False,
                "error_code": None,
            }
            assert supply.isError is False
            assert supply.structuredContent == {
                "status": "connected",
                "connected": True,
                "controller_reported_voltage_volts": 1.3,
                "interpretation": (
                    "controller_reported_not_calibrated_or_independent_power_safety"
                ),
                "error_code": None,
            }
            assert fixture.received == [b"\x80\x00\x81", b"\x80\x0a\x81"]


@pytest.mark.anyio
async def test_motion_tool_rejects_before_socket_and_rejects_extra_input(
    tmp_path: Path,
) -> None:
    settings = GatewaySettings(
        host=IPv4Address("127.0.0.1"),
        port=1,
        timeout_seconds=0.5,
    )
    settings_path = tmp_path / "settings.json"
    _ = settings_path.write_text(settings.model_dump_json(), encoding="utf-8")
    parameters = StdioServerParameters(
        command=sys.executable,
        args=[
            "-m",
            "furbomek_gateway",
            "serve",
            "--settings",
            str(settings_path),
        ],
        cwd=PROJECT_ROOT,
    )

    async with (
        stdio_client(parameters) as (read_stream, write_stream),
        ClientSession(read_stream, write_stream) as session,
    ):
        _ = await session.initialize()
        rejected = await session.call_tool(
            "robot_request_motion",
            {
                "request": {
                    "leg": 1,
                    "delta_x": 0,
                    "delta_y": 0,
                    "delta_z": 0,
                    "duration_ms": 100,
                }
            },
        )
        invalid = await session.call_tool(
            "robot_request_motion",
            {
                "request": {
                    "leg": 1,
                    "delta_x": 0,
                    "delta_y": 0,
                    "delta_z": 0,
                    "duration_ms": 100,
                    "extra": 1,
                }
            },
        )

        assert rejected.isError is False
        assert rejected.structuredContent == {
            "decision": "rejected",
            "reason": "local_safety_unqualified",
            "sent": False,
            "network_accessed": False,
        }
        assert invalid.isError is True
