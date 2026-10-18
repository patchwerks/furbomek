import anyio
import pytest

from furbomek_gateway.guard_gateway import GuardService
from furbomek_gateway.guard_models import GuardSettings, MotorOffCheckResult
from furbomek_gateway.guard_protocol import GuardCommand
from furbomek_gateway.guard_serial import GuardSerialTransport
from tests.guard_support import PtyGuardBoard


def settings(path: str) -> GuardSettings:
    return GuardSettings(
        bridge_device_path=path,
        mode="motor_off_bench",
        operator_profile="operator_confirmed_motor_off_bench",
        exchange_timeout_seconds=0.1,
        active_check_timeout_ms=2000,
    )


@pytest.mark.anyio
async def test_concurrent_stop_cancels_active_check_and_clears_ownership() -> None:
    with PtyGuardBoard(auto_complete=False, stop_reply_copies=3) as board:
        service = GuardService(settings(board.path))
        await service.open()
        results: list[MotorOffCheckResult] = []

        async def check() -> None:
            results.append(await service.run_motor_off_check())

        try:
            with anyio.fail_after(1):
                async with anyio.create_task_group() as tasks:
                    _ = tasks.start_soon(check)
                    assert await anyio.to_thread.run_sync(board.executed.wait, 0.5)
                    _ = tasks.start_soon(service.stop)
                    _ = tasks.start_soon(service.stop)
            assert results[0].reason == "cancelled"
            assert results[0].stop_frame_sent
            assert results[0].fault_verified
            assert (await service.run_motor_off_check()).reason == "guard_not_boot"
            assert board.stop_received.is_set()
        finally:
            await service.aclose()


@pytest.mark.anyio
async def test_unsolicited_completion_is_not_a_failed_exchange() -> None:
    with PtyGuardBoard(auto_complete=False, unsolicited_completion=True) as board:
        service = GuardService(settings(board.path))
        await service.open()
        try:
            result = await service.run_motor_off_check()
        finally:
            await service.aclose()
    assert result.decision == "completed"
    assert result.busy_cleared
    assert result.fault_verified


@pytest.mark.anyio
async def test_fault_clearing_busy_is_not_successful_completion() -> None:
    with PtyGuardBoard(fault_on_completion=True) as board:
        service = GuardService(settings(board.path))
        await service.open()
        try:
            result = await service.run_motor_off_check()
        finally:
            await service.aclose()
    assert result.decision != "completed"
    assert not result.busy_cleared
    assert result.stop_frame_sent


@pytest.mark.anyio
async def test_disconnect_during_active_polling_ends_check_and_heartbeat() -> None:
    with PtyGuardBoard(auto_complete=False) as board:
        service = GuardService(settings(board.path))
        await service.open()
        results: list[MotorOffCheckResult] = []

        async def check() -> None:
            results.append(await service.run_motor_off_check())

        try:
            with anyio.fail_after(1):
                async with anyio.create_task_group() as tasks:
                    _ = tasks.start_soon(check)
                    assert await anyio.to_thread.run_sync(
                        board.heartbeat_received.wait, 0.5
                    )
                    board.disconnect()
            assert results[0].reason == "transport_failure"
            assert not results[0].busy_cleared
            assert (await service.run_motor_off_check()).reason == "transport_failure"
        finally:
            await service.aclose()


@pytest.mark.anyio
async def test_two_concurrent_commands_allocate_distinct_sequences() -> None:
    with PtyGuardBoard() as board:
        transport = await GuardSerialTransport.open(settings(board.path))
        try:
            _ = await transport.begin(b"sequence")
            async with anyio.create_task_group() as tasks:
                _ = tasks.start_soon(transport.command, GuardCommand.STATUS)
                _ = tasks.start_soon(transport.command, GuardCommand.STATUS)
        finally:
            await transport.aclose()
    sequences = [frame[3] for frame in board.received if frame[2] == 0x32]
    assert sequences == [1, 2]


@pytest.mark.anyio
async def test_stop_on_closed_port_does_not_claim_delivery() -> None:
    with PtyGuardBoard() as board:
        transport = await GuardSerialTransport.open(settings(board.path))
        await transport.aclose()
        result = await transport.stop()
    assert not result.frame_sent
    assert result.reply is None
