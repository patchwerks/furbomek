"""Disabled-by-default local PTY sequencer; production release remains HOLD."""

import os
from collections.abc import Callable
from contextlib import ExitStack
from types import TracebackType
from typing import Final, Self, final

import anyio

from furbomek_gateway.guard_gateway import GuardService
from furbomek_gateway.guard_models import GuardSettings, GuardStopResult
from furbomek_gateway.motion_sequence_models import (
    OfflineQualification,
    SequenceObserver,
    SequenceRequest,
    SequenceResult,
    StepVerdict,
)
from furbomek_gateway.stage_admission import verify_stage

MAX_STAGE_MS: Final = 30000


class SequencePermissionError(ValueError):
    """A physical device or unqualified local comparison was requested."""


@final
class MotionSequence:
    """Own a finite queue over unchanged complete Guard action lifecycles.

    This constructor never opens a device. Only a PTY comparison can enter the
    context manager; real hardware needs a separate trusted installed-receipt
    verifier and measured sequence acceptance, neither supplied by JSON here.
    """

    def __init__(self, settings: GuardSettings, observer: SequenceObserver) -> None:
        """Create disabled local sequence state with no serial activity."""
        self._settings = settings
        self._observer = observer
        self._guard = GuardService(settings)
        self._resources = ExitStack()
        self.pty_master_fd: int | None = None
        self._qualification = OfflineQualification(valid_from_ms=0, valid_until_ms=0)
        self._clock: Callable[[], int] = lambda: int(anyio.current_time() * 1000)
        self._active: anyio.CancelScope | None = None
        self._opened = False
        self._stopped = False

    def configure_offline(
        self, qualification: OfflineQualification, clock: Callable[[], int]
    ) -> None:
        """Inject local comparison scope; never accept an actuator permit."""
        if self._opened:
            reason = "configuration_locked"
            raise SequencePermissionError(reason)
        self._qualification = qualification
        self._clock = clock

    async def __aenter__(self) -> Self:
        """Allocate an owned PTY; never open the supplied device setting."""
        q = self._qualification
        if not q.enabled or self._opened:
            reason = "offline_pty_only_production_HOLD"
            raise SequencePermissionError(reason)
        with ExitStack() as resources:
            master, slave = os.openpty()
            _ = resources.callback(os.close, master)
            _ = resources.callback(os.close, slave)
            self.pty_master_fd = master
            self._guard = GuardService(
                self._settings.model_copy(
                    update={"bridge_device_path": os.ttyname(slave)}
                )
            )
            await self._guard.open()
            self._resources = resources.pop_all()
        self._opened = True
        return self

    async def __aexit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc: BaseException | None,
        _traceback: TracebackType | None,
    ) -> None:
        """Close with priority cancellation and the runner's shielded cleanup."""
        self._stopped = True
        if self._active is not None:
            _ = await self.stop()
        try:
            await self._guard.aclose()
        finally:
            self._resources.close()
            self.pty_master_fd = None
            self._opened = False

    async def stop(self) -> GuardStopResult:
        """Invalidate all queued steps and bypass every admission/operation gate."""
        self._stopped = True
        if self._active is not None:
            self._active.cancel()
        result = GuardStopResult(
            available=False,
            stop_frame_sent=False,
            fault_verified=False,
            physical_reset_required=None,
        )
        with anyio.CancelScope(shield=True):
            return await self._guard.stop()
        return result

    async def run(self, request: SequenceRequest) -> SequenceResult:
        """Execute one queue; reject competing queues and never retry a step."""
        q = self._qualification
        if not self._opened or not q.enabled or self._stopped:
            return SequenceResult(status="HOLD", reason="disabled_or_stopped")
        if self._active is not None:
            return SequenceResult(status="HOLD", reason="queue_busy")
        start = self._clock()
        deadline = min(start + request.duration_ms, q.valid_until_ms)
        if (
            not q.valid_from_ms <= start < deadline
            or q.valid_until_ms - q.valid_from_ms > MAX_STAGE_MS
        ):
            return SequenceResult(status="HOLD", reason="qualification_expired")
        verdicts: list[StepVerdict] = []
        result = SequenceResult(status="cancelled", reason="priority_stop")
        with anyio.CancelScope() as scope:
            self._active = scope
            try:
                with anyio.fail_after((deadline - start) / 1000):
                    result = await self._run_steps(request, deadline, verdicts)
            except TimeoutError:
                result = SequenceResult(status="uncertain", reason="stage_timeout")
            finally:
                with anyio.CancelScope(shield=True):
                    if result.status != "completed":
                        self._stopped = True
                        _ = await self._guard.stop()
                    self._active = None
        if scope.cancel_called:
            result = SequenceResult(status="cancelled", reason="priority_stop")
        return result.model_copy(update={"steps": tuple(verdicts)})

    async def _run_steps(
        self, request: SequenceRequest, deadline: int, verdicts: list[StepVerdict]
    ) -> SequenceResult:
        q = self._qualification
        previous: str | None = None
        for step in request.steps:
            now = self._clock()
            # Reserve complete two-phase forward plus all exchanges and DISARM.
            budget = (
                self._settings.action_timeout_ms
                * (2 if step.action == "forward" else 1)
                + 1500
            )
            if self._stopped or now < q.valid_from_ms or now + budget >= deadline:
                return SequenceResult(status="HOLD", reason="stage_budget_exhausted")
            if step.profile_id not in q.profile_ids or (
                previous is not None
                and (previous, step.profile_id) not in q.transitions
            ):
                return SequenceResult(status="HOLD", reason="unqualified_transition")
            observed = self._observer.before_step(step)
            now = self._clock()
            if now + budget >= deadline:
                return SequenceResult(status="HOLD", reason="stage_budget_exhausted")
            observed = observed.model_copy(
                update={"context": observed.context.model_copy(update={"now_ms": now})}
            )
            receipt = verify_stage(observed)
            profile = observed.context.profile
            if (
                not receipt.local_checks_passed
                or profile.profile_id != step.profile_id
                or profile.action != step.action
            ):
                verdicts.append(StepVerdict(stage=receipt))
                return SequenceResult(status="HOLD", reason="stage_check_failed")
            guard = await self._guard.perform_action(step.action)
            optical = self._observer.after_step(step)
            verdicts.append(StepVerdict(stage=receipt, guard=guard, optical=optical))
            healthy = guard.decision == "completed" and guard.disarm_acknowledged
            if not healthy or optical != "pass" or self._clock() >= deadline:
                return SequenceResult(
                    status="uncertain", reason="step_uncertain_or_expired"
                )
            previous = step.profile_id
        return SequenceResult(
            status="completed", reason="offline_completed_and_disarmed"
        )
