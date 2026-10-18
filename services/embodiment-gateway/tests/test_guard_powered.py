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
async def test_two_powered_actions_return_to_disarmed_without_panic_stop() -> None:
    with PtyGuardBoard(supply_centivolts=800, strict_sequence=True) as board:
        service = GuardService(powered_settings(board.path, ("active", "forward")))
        await service.open()
        try:
            first = await service.perform_action("active")
            second = await service.perform_action("forward")
        finally:
            await service.aclose()

    assert first.decision == "completed"
    assert first.disarm_acknowledged
    assert first.physical_reset_required is False
    assert second.decision == "completed"
    assert second.disarm_acknowledged
    assert second.physical_reset_required is False
    assert board.actions == [0, 2]
    assert b"\x80\x30\x81" not in board.received


@pytest.mark.anyio
async def test_powered_action_resumes_global_sequence_after_service_restart() -> None:
    with PtyGuardBoard(supply_centivolts=800, strict_sequence=True) as board:
        first_service = GuardService(powered_settings(board.path))
        await first_service.open()
        first = await first_service.perform_action("active")
        await first_service.aclose()

        second_service = GuardService(powered_settings(board.path))
        await second_service.open()
        try:
            state = await second_service.get_state()
            second = await second_service.perform_action("active")
        finally:
            await second_service.aclose()

    assert first.decision == "completed"
    assert state.guard_state == "disarmed"
    assert second.decision == "completed"
    assert board.actions == [0, 0]
    assert b"\x80\x30\x81" not in board.received


@pytest.mark.anyio
async def test_powered_policy_refusal_does_not_begin_or_stop() -> None:
    with PtyGuardBoard(supply_centivolts=900, strict_sequence=True) as board:
        service = GuardService(powered_settings(board.path))
        await service.open()
        try:
            result = await service.perform_action("forward")
        finally:
            await service.aclose()

    assert result.decision == "refused"
    assert result.reason == "action_not_qualified"
    assert board.received == []


@pytest.mark.anyio
async def test_powered_voltage_refusal_does_not_begin() -> None:
    with PtyGuardBoard(supply_centivolts=600, strict_sequence=True) as board:
        service = GuardService(powered_settings(board.path))
        await service.open()
        try:
            result = await service.perform_action("active")
        finally:
            await service.aclose()

    assert result.decision == "refused"
    assert result.reason == "supply_gate_failed"
    assert [frame[2] for frame in board.received] == [0x34]


@pytest.mark.anyio
async def test_bad_disarm_ack_sends_stop_and_does_not_claim_disarmed() -> None:
    with PtyGuardBoard(
        supply_centivolts=800,
        strict_sequence=True,
        bad_disarm_ack=True,
    ) as board:
        service = GuardService(powered_settings(board.path))
        await service.open()
        try:
            result = await service.perform_action("active")
        finally:
            await service.aclose()

    assert result.decision == "unavailable"
    assert result.reason == "disarm_rejected"
    assert not result.disarm_acknowledged
    assert result.stop_frame_sent
    assert result.fault_verified


@pytest.mark.anyio
async def test_concurrent_stop_faults_powered_action() -> None:
    with PtyGuardBoard(
        supply_centivolts=800,
        strict_sequence=True,
        auto_complete=False,
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
                    assert await anyio.to_thread.run_sync(board.executed.wait, 0.5)
                    _ = tasks.start_soon(service.stop)
            second = await service.perform_action("active")
        finally:
            await service.aclose()

    assert results[0].decision == "unavailable"
    assert not results[0].disarm_acknowledged
    assert results[0].fault_verified
    assert second.decision != "completed"
    assert board.stop_received.is_set()


@pytest.mark.anyio
async def test_disconnect_after_exec_ack_preserves_action_accepted_fact() -> None:
    with PtyGuardBoard(supply_centivolts=800, strict_sequence=True) as board:
        service = GuardService(powered_settings(board.path))
        await service.open()
        results: list[PoweredActionResult] = []
        try:
            async with anyio.create_task_group() as tasks:

                async def run_action() -> None:
                    results.append(await service.perform_action("active"))

                _ = tasks.start_soon(run_action)
                assert await anyio.to_thread.run_sync(
                    board.heartbeat_received.wait, 0.5
                )
                board.disconnect()
        finally:
            await service.aclose()

    assert results
    result = results[0]
    assert result.action_accepted
    assert not result.disarm_acknowledged


@pytest.mark.anyio
async def test_external_cancel_after_exec_propagates_and_clears_owner() -> None:
    with PtyGuardBoard(
        supply_centivolts=800,
        strict_sequence=True,
        auto_complete=False,
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
                    assert await anyio.to_thread.run_sync(board.executed.wait, 0.5)
                    tasks.cancel_scope.cancel()
            assert propagated.is_set()
            second = await service.perform_action("active")
        finally:
            await service.aclose()

    assert second.decision != "completed"
    assert board.stop_received.is_set()
