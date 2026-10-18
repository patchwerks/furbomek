import threading

import anyio
import pytest
import serial

from furbomek_gateway.guard_gateway import GuardService
from furbomek_gateway.guard_protocol import GuardState
from furbomek_gateway.guard_serial import GuardSerialTransport, StopExchange
from tests.guard_support import PtyGuardBoard
from tests.test_guard_lifecycle import settings


@pytest.mark.anyio
async def test_stop_write_remains_true_when_peer_disconnects_before_ack() -> None:
    with PtyGuardBoard(disconnect_on_stop=True) as board:
        transport = await GuardSerialTransport.open(settings(board.path))
        try:
            result = await transport.stop()
        finally:
            await transport.aclose()
    assert result.frame_sent
    assert result.reply is None
    assert board.stop_received.is_set()


@pytest.mark.anyio
async def test_external_cancel_propagates_after_terminal_stop_and_cleanup() -> None:
    with PtyGuardBoard(auto_complete=False) as board:
        service = GuardService(settings(board.path))
        await service.open()
        propagated = anyio.Event()

        async def check() -> None:
            try:
                _ = await service.run_motor_off_check()
            except anyio.get_cancelled_exc_class():
                propagated.set()
                raise

        try:
            with anyio.fail_after(1):
                async with anyio.create_task_group() as tasks:
                    _ = tasks.start_soon(check)
                    assert await anyio.to_thread.run_sync(board.executed.wait, 0.5)
                    tasks.cancel_scope.cancel()
            assert propagated.is_set()
            assert board.stop_received.is_set()
            assert (await service.run_motor_off_check()).reason == "guard_not_boot"
        finally:
            await service.aclose()


@pytest.mark.anyio
async def test_cancelled_partial_reply_does_not_corrupt_following_stop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_read = serial.Serial.read
    first_chunk_read = threading.Event()
    release_read = threading.Event()

    def read(port: serial.Serial, size: int = 1) -> bytes:
        chunk = original_read(port, size)
        if len(chunk) == 8:
            first_chunk_read.set()
            _ = release_read.wait(timeout=1)
        return chunk

    monkeypatch.setattr(serial.Serial, "read", read)
    with PtyGuardBoard(partial_supply=True) as board:
        transport = await GuardSerialTransport.open(settings(board.path))
        query_done = anyio.Event()
        query_started = anyio.Event()
        query_scope = anyio.CancelScope()
        result: StopExchange | None = None

        async def query() -> None:
            with query_scope:
                query_started.set()
                _ = await transport.supply()
            query_done.set()

        try:
            with anyio.fail_after(2):
                async with anyio.create_task_group() as tasks:
                    _ = tasks.start_soon(query)
                    await query_started.wait()
                    assert await anyio.to_thread.run_sync(first_chunk_read.wait, 0.5)
                    query_scope.cancel()
                    release_read.set()
                    await query_done.wait()
                    board.release_supply.set()
                    result = await transport.stop()
            assert result is not None
            assert result.frame_sent
            assert result.reply is not None
            assert result.reply.state is GuardState.FAULT
        finally:
            release_read.set()
            board.release_supply.set()
            await transport.aclose()
