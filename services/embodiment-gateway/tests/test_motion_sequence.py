import errno
import os
from typing import Literal, assert_never

import anyio
import pytest
from pydantic import ValidationError

from furbomek_gateway.motion_sequence import MotionSequence, SequencePermissionError
from furbomek_gateway.motion_sequence_models import (
    OfflineQualification,
    SequenceRequest,
    SequenceResult,
)
from tests.guard_settings import powered_settings
from tests.motion_sequence_support import Observer, OwnedBoard, queue, sequence


@pytest.mark.anyio
async def test_owned_pty_runs_forward_phases_and_disarms_each_step() -> None:
    observer = Observer()
    async with sequence(observer) as runner:
        master = runner.pty_master_fd
        assert master is not None
        with OwnedBoard(runner).serve() as board:
            result = await runner.run(queue(observer))
            assert result.status == "completed"
            assert board.actions == [2, 2, 2, 2]
            assert [frame[2] for frame in board.received].count(0x36) == 2
            assert not board.stop_received.is_set()
            assert all(s.guard and s.guard.disarm_acknowledged for s in result.steps)
            assert [s.optical for s in result.steps] == ["pass", "pass"]
            assert not result.physical_motion_authorized
    with pytest.raises(OSError, match="Bad file descriptor") as closed:
        _ = os.fstat(master)
    assert closed.value.errno == errno.EBADF


@pytest.mark.anyio
async def test_default_disabled_does_not_open_supplied_device() -> None:
    runner = MotionSequence(powered_settings("/never/open/this"), Observer())
    with pytest.raises(SequencePermissionError, match="production_HOLD"):
        async with runner:
            pytest.fail("disabled runner opened")


@pytest.mark.anyio
@pytest.mark.parametrize("advance", [601, 20000])
async def test_stale_pose_or_expiry_cancels_next_mutation(advance: int) -> None:
    observer = Observer()
    observer.advance = advance
    async with sequence(observer) as runner:
        with OwnedBoard(runner).serve() as board:
            result = await runner.run(queue(observer))
            assert result.status in {"HOLD", "uncertain"}
            assert board.actions == [2, 2]
            assert board.stop_received.is_set()


@pytest.mark.anyio
async def test_unqualified_transition_cancels_after_disarm() -> None:
    observer = Observer()
    runner = sequence(observer)
    runner.configure_offline(
        OfflineQualification(
            enabled=True,
            profile_ids=(observer.stage.context.profile.profile_id,),
            valid_from_ms=10000,
            valid_until_ms=30000,
        ),
        observer.clock,
    )
    async with runner:
        with OwnedBoard(runner).serve() as board:
            result = await runner.run(queue(observer))
            assert result.reason == "unqualified_transition"
            assert board.actions == [2, 2]


@pytest.mark.anyio
async def test_priority_stop_preempts_queue_without_next_phase() -> None:
    observer = Observer()
    results: list[SequenceResult] = []
    async with sequence(observer) as runner:
        with OwnedBoard(runner).serve() as board:
            board.auto_complete = False

            async def run() -> None:
                results.append(await runner.run(queue(observer)))

            async with anyio.create_task_group() as tasks:
                _ = tasks.start_soon(run)
                assert await anyio.to_thread.run_sync(board.executed.wait, 1)
                competing = await runner.run(queue(observer))
                assert competing.reason == "queue_busy"
                stopped = await runner.stop()
                assert stopped.stop_frame_sent
            assert results[0].status == "cancelled"
            assert board.actions == [2]
            assert (await runner.run(queue(observer))).reason == "disabled_or_stopped"


@pytest.mark.anyio
@pytest.mark.parametrize("failure", ["ack", "rf", "optical", "second_ack"])
async def test_ambiguous_completion_stops_without_next_mutation(
    failure: Literal["ack", "rf", "optical", "second_ack"],
) -> None:
    observer = Observer()
    async with sequence(observer) as runner:
        with OwnedBoard(runner).serve() as board:
            match failure:
                case "ack":
                    board.wrong_disarm_sequence = True
                case "rf":
                    board.drop_keep_replies = 20
                case "optical":
                    observer.optical = "uncertain"
                case "second_ack":
                    board.drop_second_exec_ack = True
                case _:
                    assert_never(failure)
            result = await runner.run(queue(observer))
            assert result.status == "uncertain"
            assert len(board.actions) == (1 if failure == "rf" else 2)
            assert board.stop_received.is_set()


@pytest.mark.parametrize(
    "extra", ["permit", "physical_motion_authorized", "installed_receipt"]
)
def test_request_cannot_mint_authority(extra: str) -> None:
    raw = queue(Observer()).model_dump()
    raw[extra] = True
    with pytest.raises(ValidationError):
        _ = SequenceRequest.model_validate(raw)


@pytest.mark.anyio
@pytest.mark.parametrize("condition", ["expired", "overlong", "unselected", "boundary"])
async def test_initial_hold_emits_no_arm_or_exec(condition: str) -> None:
    observer = Observer()
    runner = sequence(observer)
    profile = observer.stage.context.profile.profile_id
    runner.configure_offline(
        OfflineQualification(
            enabled=True,
            profile_ids=() if condition == "unselected" else (profile,),
            transitions=((profile, profile),),
            valid_from_ms=0 if condition == "overlong" else 10000,
            valid_until_ms=40000 if condition == "overlong" else 30000,
        ),
        observer.clock,
    )
    if condition == "expired":
        observer.now = 30001
    if condition == "boundary":
        current = observer.stage.current
        observer.stage = observer.stage.model_copy(
            update={
                "current": current.model_copy(
                    update={"start": current.start.model_copy(update={"x_mm": -50.0})}
                )
            }
        )
    async with runner:
        with OwnedBoard(runner).serve() as board:
            result = await runner.run(queue(observer))
            assert result.status == "HOLD"
            assert board.actions == []
            assert not any(frame[2] == 0x2A for frame in board.received)
