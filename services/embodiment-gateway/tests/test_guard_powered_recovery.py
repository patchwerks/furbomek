from __future__ import annotations

from typing import TYPE_CHECKING

import anyio
import pytest

from furbomek_gateway.guard_gateway import GuardService
from tests.guard_settings import powered_settings
from tests.guard_support import PtyGuardBoard

if TYPE_CHECKING:
    from furbomek_gateway.guard_models import PoweredActionResult


@pytest.mark.anyio
async def test_wrong_disarm_sequence_is_stale_and_panics_stop() -> None:
    with PtyGuardBoard(
        supply_centivolts=800,
        strict_sequence=True,
        wrong_disarm_sequence=True,
    ) as board:
        service = GuardService(powered_settings(board.path))
        await service.open()
        try:
            result = await service.perform_action("active")
        finally:
            await service.aclose()

    assert result.decision == "unavailable"
    assert not result.disarm_acknowledged
    assert result.stop_frame_sent
    assert result.fault_verified


@pytest.mark.parametrize("initial_state", [1, 4])
@pytest.mark.anyio
async def test_owned_or_fault_state_refuses_before_begin_without_stop(
    initial_state: int,
) -> None:
    with PtyGuardBoard(
        supply_centivolts=800,
        strict_sequence=True,
        initial_state=initial_state,
    ) as board:
        service = GuardService(powered_settings(board.path))
        await service.open()
        try:
            result = await service.perform_action("active")
        finally:
            await service.aclose()

    assert result.reason == "guard_not_ready"
    assert result.decision == "unavailable"
    assert [frame[2] for frame in board.received] == [0x34, 0x32]
    assert b"\x80\x30\x81" not in board.received


@pytest.mark.anyio
async def test_stop_during_begin_ack_cleans_owner_and_stops() -> None:
    with PtyGuardBoard(
        supply_centivolts=800,
        strict_sequence=True,
        hold_begin_reply=True,
    ) as board:
        service = GuardService(powered_settings(board.path))
        await service.open()
        results: list[PoweredActionResult] = []

        async def run_action() -> None:
            results.append(await service.perform_action("active"))

        try:
            with anyio.fail_after(1):
                async with anyio.create_task_group() as tasks:
                    _ = tasks.start_soon(run_action)
                    assert await anyio.to_thread.run_sync(
                        board.begin_received.wait, 0.5
                    )
                    _ = await service.stop()
            second = await service.perform_action("active")
        finally:
            await service.aclose()

    assert results[0].stop_frame_sent
    assert second.decision != "completed"


@pytest.mark.anyio
async def test_external_cancel_before_begin_status_does_not_stop() -> None:
    with PtyGuardBoard(
        supply_centivolts=800,
        strict_sequence=True,
        hold_status_reply=True,
    ) as board:
        service = GuardService(powered_settings(board.path))
        await service.open()
        propagated = anyio.Event()

        async def run_action() -> None:
            try:
                _ = await service.perform_action("active")
            except anyio.get_cancelled_exc_class():
                propagated.set()
                raise

        try:
            with anyio.fail_after(1):
                async with anyio.create_task_group() as tasks:
                    _ = tasks.start_soon(run_action)
                    assert await anyio.to_thread.run_sync(
                        board.status_received.wait, 0.5
                    )
                    tasks.cancel_scope.cancel()
            assert propagated.is_set()
        finally:
            await service.aclose()

    assert [frame[2] for frame in board.received] == [0x34, 0x32]
    assert b"\x80\x30\x81" not in board.received


@pytest.mark.anyio
async def test_one_keep_ack_loss_retries_exact_query_without_exec_retry() -> None:
    with PtyGuardBoard(
        supply_centivolts=800,
        strict_sequence=True,
        drop_first_keep_reply=True,
    ) as board:
        service = GuardService(powered_settings(board.path))
        await service.open()
        try:
            result = await service.perform_action("active")
        finally:
            await service.aclose()

    assert result.decision == "completed"
    assert board.actions == [0]
    assert [frame[2] for frame in board.received].count(0x2C) == 2


@pytest.mark.anyio
async def test_double_keep_ack_loss_stops_without_exec_retry() -> None:
    with PtyGuardBoard(
        supply_centivolts=800,
        strict_sequence=True,
        drop_keep_replies=2,
    ) as board:
        service = GuardService(powered_settings(board.path))
        await service.open()
        try:
            result = await service.perform_action("active")
        finally:
            await service.aclose()

    assert result.decision == "unavailable"
    assert result.stop_frame_sent
    assert board.actions == [0]
    assert [frame[2] for frame in board.received].count(0x2C) == 2


@pytest.mark.anyio
async def test_late_duplicate_keep_ack_is_drained_before_fresh_query() -> None:
    with PtyGuardBoard(
        supply_centivolts=800,
        strict_sequence=True,
        auto_complete=False,
        complete_after_keep_count=2,
        keep_reply_copies=2,
    ) as board:
        service = GuardService(powered_settings(board.path))
        await service.open()
        try:
            result = await service.perform_action("active")
        finally:
            await service.aclose()

    assert result.decision == "completed"
    assert [frame[2] for frame in board.received].count(0x2C) == 2


@pytest.mark.anyio
async def test_low_query_lease_budget_stops_before_disarm() -> None:
    with PtyGuardBoard(
        supply_centivolts=800,
        strict_sequence=True,
        query_remaining_ms=100,
    ) as board:
        service = GuardService(powered_settings(board.path))
        await service.open()
        try:
            result = await service.perform_action("active")
        finally:
            await service.aclose()

    assert result.decision == "unavailable"
    assert not result.disarm_acknowledged
    assert result.stop_frame_sent
    assert result.lease_lower_bound_ms is not None
    assert result.lease_lower_bound_ms < 130
