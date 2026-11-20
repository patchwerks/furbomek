import os
import threading
from collections.abc import Generator
from contextlib import contextmanager
from typing import Literal, Self, final, override

from furbomek_gateway.motion_sequence import MotionSequence
from furbomek_gateway.motion_sequence_models import (
    OfflineQualification,
    SequenceRequest,
    SequenceStep,
)
from furbomek_gateway.stage_models import StageRequest
from tests.guard_settings import powered_settings
from tests.guard_support import PtyGuardBoard
from tests.test_stage_admission import request


@final
class Observer:
    def __init__(self) -> None:
        self.now = 10000
        self.advance = 0
        self.optical: Literal["pass", "fail", "uncertain"] = "pass"
        self.stage = request()

    def clock(self) -> int:
        return self.now

    def before_step(self, _step: SequenceStep) -> StageRequest:
        return self.stage

    def after_step(self, _step: SequenceStep) -> Literal["pass", "fail", "uncertain"]:
        self.now += self.advance
        return self.optical


@final
class OwnedBoard(PtyGuardBoard):
    def __init__(self, sequence: MotionSequence) -> None:
        super().__init__(supply_centivolts=800, strict_sequence=True)
        assert sequence.pty_master_fd is not None
        self._master = os.dup(sequence.pty_master_fd)
        self.drop_second_exec_ack = False

    @contextmanager
    def serve(self) -> Generator[Self]:
        self._stop = threading.Event()
        self._disconnected = False
        self._before_start()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        try:
            yield self
        finally:
            if not self._disconnected:
                self.disconnect()

    @override
    def _write(self, data: bytes) -> None:
        if self.drop_second_exec_ack and data[2] == 0x2F and len(self.actions) == 2:
            return
        super()._write(data)


def sequence(observer: Observer) -> MotionSequence:
    runner = MotionSequence(
        powered_settings("/never/open/this", ("forward",)), observer
    )
    profile = observer.stage.context.profile.profile_id
    runner.configure_offline(
        OfflineQualification(
            enabled=True,
            profile_ids=(profile,),
            transitions=((profile, profile),),
            valid_from_ms=10000,
            valid_until_ms=30000,
        ),
        observer.clock,
    )
    return runner


def queue(observer: Observer) -> SequenceRequest:
    step = SequenceStep(
        profile_id=observer.stage.context.profile.profile_id, action="forward"
    )
    return SequenceRequest(steps=(step, step), duration_ms=10000)
