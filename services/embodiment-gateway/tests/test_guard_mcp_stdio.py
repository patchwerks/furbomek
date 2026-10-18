import sys
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from furbomek_gateway.guard_models import (
    GuardSettings,
    MotorOffCheckResult,
    PoweredActionResult,
)
from tests.guard_support import PtyGuardBoard

_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.anyio
async def test_guard_stdio_lists_and_calls_state_supply_and_real_stop(
    tmp_path: Path,
) -> None:
    with PtyGuardBoard() as board:
        settings = GuardSettings(
            bridge_device_path=board.path,
            mode="motor_off_bench",
            operator_profile="operator_confirmed_motor_off_bench",
        )
        path = tmp_path / "guard.json"
        _ = path.write_text(settings.model_dump_json(), encoding="utf-8")
        parameters = StdioServerParameters(
            command=sys.executable,
            args=["-m", "furbomek_gateway", "serve-guard", "--settings", str(path)],
            cwd=_ROOT,
        )
        async with (
            stdio_client(parameters) as (read_stream, write_stream),
            ClientSession(read_stream, write_stream) as session,
        ):
            _ = await session.initialize()
            names = tuple(
                sorted(tool.name for tool in (await session.list_tools()).tools)
            )
            state = await session.call_tool("robot_get_state")
            supply = await session.call_tool("robot_get_supply_voltage")
            stop = await session.call_tool("robot_stop")
        assert names == (
            "robot_get_capabilities",
            "robot_get_state",
            "robot_get_supply_voltage",
            "robot_perform_action",
            "robot_run_motor_off_check",
            "robot_stop",
        )
    assert state.structuredContent is not None
    assert supply.structuredContent is not None
    assert stop.structuredContent is not None
    assert board.received[-1] == b"\x80\x30\x81"


@pytest.mark.anyio
async def test_guard_stdio_executes_bounded_check_then_verifies_stop(
    tmp_path: Path,
) -> None:
    with PtyGuardBoard(unsolicited_completion=True) as board:
        config = GuardSettings(
            bridge_device_path=board.path,
            mode="motor_off_bench",
            operator_profile="operator_confirmed_motor_off_bench",
        )
        path = tmp_path / "guard.json"
        _ = path.write_text(config.model_dump_json(), encoding="utf-8")
        parameters = StdioServerParameters(
            command=sys.executable,
            args=["-m", "furbomek_gateway", "serve-guard", "--settings", str(path)],
            cwd=_ROOT,
        )
        async with (
            stdio_client(parameters) as (read_stream, write_stream),
            ClientSession(read_stream, write_stream) as session,
        ):
            _ = await session.initialize()
            response = await session.call_tool("robot_run_motor_off_check")
        result = MotorOffCheckResult.model_validate(response.structuredContent)
    assert result.decision == "completed"
    assert result.active_accepted
    assert result.busy_cleared
    assert result.stop_frame_sent
    assert result.fault_verified
    assert not result.physical_motion_observed


@pytest.mark.anyio
async def test_powered_stdio_executes_two_actions_without_stop_or_reset(
    tmp_path: Path,
) -> None:
    with PtyGuardBoard(supply_centivolts=800, strict_sequence=True) as board:
        config = GuardSettings(
            bridge_device_path=board.path,
            mode="supervised_powered_bench",
            operator_profile="operator_present_supported_chassis",
        )
        path = tmp_path / "powered.json"
        _ = path.write_text(config.model_dump_json(), encoding="utf-8")
        parameters = StdioServerParameters(
            command=sys.executable,
            args=["-m", "furbomek_gateway", "serve-guard", "--settings", str(path)],
            cwd=_ROOT,
        )
        async with (
            stdio_client(parameters) as (read_stream, write_stream),
            ClientSession(read_stream, write_stream) as session,
        ):
            _ = await session.initialize()
            listed = await session.list_tools()
            names = tuple(sorted(tool.name for tool in listed.tools))
            action_tool = next(
                tool for tool in listed.tools if tool.name == "robot_perform_action"
            )
            first_response = await session.call_tool(
                "robot_perform_action", {"action": "active"}
            )
            second_response = await session.call_tool(
                "robot_perform_action", {"action": "active"}
            )
            first = PoweredActionResult.model_validate(first_response.structuredContent)
            second = PoweredActionResult.model_validate(
                second_response.structuredContent
            )

    assert names == (
        "robot_get_capabilities",
        "robot_get_state",
        "robot_get_supply_voltage",
        "robot_perform_action",
        "robot_stop",
    )
    assert action_tool.annotations is not None
    assert action_tool.annotations.readOnlyHint is False
    assert action_tool.annotations.destructiveHint is True
    assert first.decision == "completed"
    assert second.decision == "completed"
    assert first.disarm_acknowledged
    assert second.disarm_acknowledged
    assert b"\x80\x30\x81" not in board.received
