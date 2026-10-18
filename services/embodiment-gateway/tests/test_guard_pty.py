import anyio
import pytest

from furbomek_gateway.guard_gateway import GuardService
from furbomek_gateway.guard_models import GuardSettings
from tests.guard_support import PtyGuardBoard


def _settings(path: str, timeout: float = 0.1) -> GuardSettings:
    return GuardSettings(
        bridge_device_path=path,
        mode="motor_off_bench",
        operator_profile="operator_confirmed_motor_off_bench",
        exchange_timeout_seconds=timeout,
        active_check_timeout_ms=300,
    )


@pytest.mark.anyio
async def test_high_supply_refuses_before_begin_arm_exec_and_sends_real_stop() -> None:
    with PtyGuardBoard(supply_centivolts=300) as board:
        service = GuardService(_settings(board.path))
        await service.open()
        try:
            result = await service.run_motor_off_check()
        finally:
            await service.aclose()
    assert result.reason == "supply_gate_failed"
    assert [frame[2] for frame in board.received if len(frame) > 3] == [0x34]
    assert board.received[-1] == b"\x80\x30\x81"


@pytest.mark.anyio
async def test_zero_supply_is_allowed_by_explicit_motor_off_gate() -> None:
    with PtyGuardBoard(supply_centivolts=0) as board:
        service = GuardService(_settings(board.path))
        await service.open()
        try:
            result = await service.run_motor_off_check()
        finally:
            await service.aclose()

    assert result.decision == "completed"
    assert result.supply_voltage_volts == 0


@pytest.mark.anyio
async def test_arm_rejection_retains_last_accepted_sequence_then_stops() -> None:
    with PtyGuardBoard(arm_result=3) as board:
        service = GuardService(_settings(board.path))
        await service.open()
        try:
            result = await service.run_motor_off_check()
        finally:
            await service.aclose()
    assert result.reason == "transport_failure"
    assert any(frame[2] == 0x2A for frame in board.received if len(frame) > 3), (
        board.received
    )
    arm = next(frame for frame in board.received if len(frame) > 3 and frame[2] == 0x2A)
    assert arm[3:6] == b"\x01\x00\x00"
    assert board.received[-1] == b"\x80\x30\x81"


@pytest.mark.anyio
async def test_hung_uart_exchange_and_stop_are_bounded() -> None:
    with PtyGuardBoard(hang_replies=True) as board:
        service = GuardService(_settings(board.path, 0.05))
        await service.open()
        try:
            with anyio.fail_after(0.3):
                result = await service.run_motor_off_check()
        finally:
            await service.aclose()
    assert result.reason == "transport_failure"
    assert board.received[-1] == b"\x80\x30\x81"


@pytest.mark.anyio
async def test_cancellation_interrupts_a_hung_exchange_and_still_sends_stop() -> None:
    with PtyGuardBoard(hang_replies=True) as board:
        service = GuardService(_settings(board.path, 0.2))
        await service.open()
        try:
            async with anyio.create_task_group() as tasks:
                _ = tasks.start_soon(service.run_motor_off_check)
                await anyio.sleep(0.02)
                tasks.cancel_scope.cancel()
        finally:
            await service.aclose()
    assert board.received[-1] == b"\x80\x30\x81"
