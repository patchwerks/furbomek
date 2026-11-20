from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from typing import Literal

import anyio
import pytest

from furbomek_gateway import edge_robot
from furbomek_gateway.edge_protocol import RobotQuery, RobotRequest, unix_ms
from furbomek_gateway.edge_robot import RobotBench
from furbomek_gateway.guard_models import ActionName, GuardCapabilitiesResult
from furbomek_gateway.guard_protocol import GuardAction
from tests.guard_settings import powered_settings
from tests.guard_support import PtyGuardBoard

ACTION_SEQUENCE: tuple[ActionName, ...] = (
    "active",
    "forward",
    "backward",
    "left",
    "right",
    "turn_left",
    "turn_right",
    "sleep",
)


@asynccontextmanager
async def _prepared_bench(
    board: PtyGuardBoard,
    monkeypatch: pytest.MonkeyPatch,
    observe: Callable[[], bool] | None = None,
) -> AsyncGenerator[RobotBench]:
    monkeypatch.setattr(edge_robot, "HANDHELD_BOOT_SECONDS", 0)
    bench = RobotBench(powered_settings(board.path, ACTION_SEQUENCE), observe)
    try:
        assert (await bench.operator("prepare")).state == "prepared_read_only"
        board.supply_centivolts = 800
        bench.tunnel_changed(connected=True)
        yield bench
    finally:
        assert (await bench.operator("close")).state == "bench_closed"


def _request(command: ActionName | RobotQuery) -> RobotRequest:
    return RobotRequest(command=command, issued_ms=unix_ms())


@pytest.mark.anyio
async def test_all_guarded_actions_run_on_one_prepared_bridge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with PtyGuardBoard(strict_sequence=True) as board:
        async with _prepared_bench(board, monkeypatch) as bench:
            assert (await bench.operator("enable")).result == "ok"
            for action in ACTION_SEQUENCE:
                reply = await bench.remote(_request(action))
                assert reply.result == "ok"
                assert reply.state == "completed_and_disarmed"
    assert board.actions == [
        GuardAction.ACTIVE,
        GuardAction.FORWARD,
        GuardAction.FORWARD,
        GuardAction.BACKWARD,
        GuardAction.LEFT,
        GuardAction.RIGHT,
        GuardAction.TURN_LEFT,
        GuardAction.TURN_RIGHT,
        GuardAction.SLEEP,
    ]
    assert not board.stop_received.is_set()


@pytest.mark.anyio
async def test_expiry_preserves_bridge_and_motion_needs_a_new_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = 1000.0
    monkeypatch.setattr(edge_robot, "monotonic", lambda: now)
    with PtyGuardBoard(strict_sequence=True) as board:
        async with _prepared_bench(board, monkeypatch) as bench:
            assert (await bench.operator("enable")).result == "ok"
            now += edge_robot.BENCH_SECONDS - edge_robot.MOTION_REQUEST_SECONDS / 2
            budget_reply = await bench.remote(_request("forward"))
            assert budget_reply.state == "motion_window_budget"
            now += edge_robot.MOTION_REQUEST_SECONDS
            bench.expire()
            assert (await bench.remote(_request("state"))).state == "guard_status"
            reply = await bench.remote(_request("forward"))
            assert reply.state == "local_powered_bench_required"
            assert not board.actions
            assert (await bench.operator("enable")).result == "ok"
            sleep = await bench.remote(_request("sleep"))
            assert sleep.state == "completed_and_disarmed"
    assert board.actions == [GuardAction.SLEEP]
    assert not board.stop_received.is_set()


@pytest.mark.anyio
@pytest.mark.parametrize("loss", ["tunnel", "tracking"])
async def test_loss_stops_inflight_motion_without_closing_usb_or_resuming(
    monkeypatch: pytest.MonkeyPatch, loss: Literal["tunnel", "tracking"]
) -> None:
    tracking_lost = anyio.Event()
    with PtyGuardBoard(strict_sequence=True, auto_complete=False) as board:
        async with _prepared_bench(
            board, monkeypatch, lambda: not tracking_lost.is_set()
        ) as bench:
            assert (await bench.operator("enable")).result == "ok"

            async def run_motion() -> None:
                interrupted = await bench.remote(_request("forward"))
                assert interrupted.state == "motion_interrupted"

            async with anyio.create_task_group() as tasks:
                _ = tasks.start_soon(run_motion)
                assert await anyio.to_thread.run_sync(board.executed.wait, 1)
                concurrent = await bench.remote(_request("sleep"))
                assert concurrent.state == "robot_request_busy"
                match loss:
                    case "tunnel":
                        bench.tunnel_changed(connected=False)
                        bench.tunnel_changed(connected=True)
                    case "tracking":
                        tracking_lost.set()
                        bench.expire()
                assert await anyio.to_thread.run_sync(board.stop_received.wait, 1)
            capabilities = await bench.remote(_request("capabilities"))
            assert capabilities.state == "read_only_bench"
            assert isinstance(capabilities.robot, GuardCapabilitiesResult)
            assert not capabilities.robot.powered_semantic_action_available
            post_loss = await bench.remote(_request("sleep"))
            assert post_loss.state == "local_powered_bench_required"
    assert board.actions == [GuardAction.FORWARD]


@pytest.mark.anyio
async def test_silent_unpowered_robot_can_use_its_already_open_bridge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(edge_robot, "HANDHELD_BOOT_SECONDS", 0)
    with PtyGuardBoard(hang_replies=True, strict_sequence=True) as board:
        bench = RobotBench(powered_settings(board.path))
        try:
            prepared = await bench.operator("prepare")
            assert prepared.state == "prepared_waiting_for_robot"
            bench.tunnel_changed(connected=True)
            assert (await bench.remote(_request("active"))).result == "refused"
            board.supply_centivolts = 800
            board.hang_replies = False
            assert (await bench.operator("enable")).result == "ok"
            assert (await bench.remote(_request("active"))).result == "ok"
        finally:
            _ = await bench.operator("close")
    assert board.actions == [GuardAction.ACTIVE]


@pytest.mark.anyio
async def test_rebooted_controller_cannot_move_on_pre_reboot_admission(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with PtyGuardBoard(strict_sequence=True) as board:
        async with _prepared_bench(board, monkeypatch) as bench:
            assert (await bench.operator("enable")).result == "ok"
            board.simulate_reboot()

            refused = await bench.remote(_request("forward"))

            assert refused.state == "guard_not_ready"
            assert (await bench.remote(_request("forward"))).result == "refused"
    assert not board.actions
    assert not board.stop_received.is_set()
