"""Finite cue sequencing with durable consume-before-dispatch and CAS release."""

from threading import RLock
from typing import final

from .effect_contracts import AppliedAck, capability_definition
from .reaction_contracts import PrivateEvent, ReactionPack
from .reaction_store import ReactionStore
from .reaction_types import (
    AdapterFaultError,
    Clock,
    Dispatch,
    Priority,
    Projection,
    ReactionAdapter,
    Reservation,
    Step,
)


@final
class ReactionScheduler:
    """One trusted host owner; tick/ACK/cancel share a serialized lifecycle.

    Physical dispatch remains locked in this implementation. The adapter is
    required, never substituted with a simulated production backend. A new
    instance consumes interrupted work before it accepts any new admission.
    """

    def __init__(
        self, store: ReactionStore, adapter: ReactionAdapter, clock: Clock
    ) -> None:
        """Claim one runtime owner and consume interrupted work before serving."""
        store.claim_scheduler()
        self.store = store
        self.adapter = adapter
        self.clock = clock
        self.enabled = True
        self._gate = RLock()
        self.recover()

    def submit(self, event: PrivateEvent, pack: ReactionPack) -> int | None:
        """Provider ingress has fixed curated priority, regardless of its strings."""
        return self.submit_trusted(event, pack, Priority.CURATED)

    def submit_trusted(
        self, event: PrivateEvent, pack: ReactionPack, priority: Priority
    ) -> int | None:
        """Local authenticated owner/operator boundary; never expose to providers."""
        with self._gate:
            if not self.enabled:
                return None
            now = self.clock.epoch_ms()
            event.require_fresh(now)
            timing = Reservation(
                now_ms=self.clock.monotonic_ms(),
                age_budget_ms=event.occurred_ms + event.max_age_ms - now,
                priority=priority,
            )
            return self.store.admit(event, pack, timing)

    def projection(self) -> tuple[Projection, ...]:
        """Project only closed public fields, never provider identities or reasons."""
        return tuple(
            Projection(
                resource=step.resource,
                status=step.status,
                media_only_hold=step.reason == "media_only_hold",
            )
            for step in self.store.steps()
        )

    def recover(self) -> None:
        """Never resume interrupted graphs, including reservation-before-dispatch."""
        with self._gate:
            ids = {
                step.event_id
                for step in self.store.steps()
                if step.active or step.status == "pending"
            }
            for step in self.store.steps():
                if step.status in ("uncertain", "completed"):
                    if capability_definition(step.cue.effect.capability).physical:
                        self.adapter.stop()
                    else:
                        self._release(step)
            for event_id in sorted(ids):
                self.cancel(event_id, "restart_consumed")

    def cancel(self, event_id: int, reason: str = "cancelled") -> None:
        """Consume pending/uncertain work; release only the exact applied lease."""
        with self._gate:
            for step in self.store.steps():
                if step.event_id != event_id or not (
                    step.active or step.status == "pending"
                ):
                    continue
                status = "uncertain" if step.active else "cancelled"
                after = step.model_copy(update={"status": status, "reason": reason})
                if self.store.transition(step, after) and step.active:
                    if capability_definition(step.cue.effect.capability).physical:
                        self.adapter.stop()
                    else:
                        self._release(step)

    def stop(self) -> None:
        """Physical/Guard STOP bypasses cue priority and latches new admission off."""
        self.enabled = False
        self.adapter.stop()
        with self._gate:
            for event_id in sorted({s.event_id for s in self.store.steps()}):
                self.cancel(event_id, "stop")

    def _release(self, step: Step) -> None:
        current = self.adapter.snapshot(step.resource)
        if current.owner != step.owner:
            return
        if step.ack is not None:
            if current.revision != step.ack.revision:
                return
            _ = self.adapter.release(current, step.previous)
        else:
            # A dispatch without a durable ACK may have applied: neutralize only
            # its exact token, never restore an unproven previous revision.
            _ = self.adapter.release(current, None)

    def acknowledge(self, ack: AppliedAck) -> bool:
        """Accept one timely actual applied receipt matching the current lease."""
        with self._gate:
            matches = [s for s in self.store.steps() if s.owner == ack.owner]
            if not matches:
                return False
            step = matches[0]
            current = self.adapter.snapshot(step.resource)
            now = self.clock.monotonic_ms()
            if (
                step.status != "dispatched"
                or step.previous is None
                or now >= step.deadline_ms
                or not self.enabled
                or ack.cue_id != step.cue.id
                or ack.effective != step.cue.effect
                or ack.capability != step.cue.effect.capability
                or ack.resource != step.resource
                or ack.previous_revision != step.previous.revision
                or current.owner != step.owner
                or current.revision != ack.revision
                or current.effect != ack.effective
            ):
                return False
            after = step.model_copy(update={"status": "applied", "ack": ack})
            return self.store.transition(step, after)

    def tick(self) -> None:
        """Advance without sleeping; all deadlines use the same host monotonic time."""
        with self._gate:
            now = self.clock.monotonic_ms()
            for step in self.store.steps():
                if not step.active:
                    continue
                if not self.adapter.available(step.resource):
                    self.cancel(step.event_id, "media_only_hold")
                elif (
                    step.status == "applied"
                    and step.end_ms is not None
                    and now >= step.end_ms
                ):
                    after = step.model_copy(update={"status": "completed"})
                    if self.store.transition(step, after):
                        self._release(step)
                elif now >= step.deadline_ms:
                    self.cancel(step.event_id, "ack_timeout")
            for step in sorted(
                self.store.steps(), key=lambda s: (-s.priority, s.event_id, s.ordinal)
            ):
                if step.status == "pending":
                    self._advance(step, now)

    def _advance(self, step: Step, now: int) -> None:
        if step not in self.store.steps() or not self.enabled:
            self.cancel(step.event_id, "disabled")
            return
        if now + step.cue.effect.duration_ms > step.deadline_ms:
            _ = self.store.transition(
                step, step.model_copy(update={"status": "expired", "reason": "expired"})
            )
            return
        related = {
            s.cue.id: s for s in self.store.steps() if s.event_id == step.event_id
        }
        if now < step.due_ms or any(
            related[key].status not in ("completed", "skipped")
            for key in step.cue.after
        ):
            return
        definition = capability_definition(step.cue.effect.capability)
        if (
            definition.physical
            or not definition.available
            or not self.adapter.available(step.resource)
        ):
            if step.cue.on_unavailable == "cancel_pack":
                self.cancel(step.event_id, "media_only_hold")
            else:
                _ = self.store.transition(
                    step,
                    step.model_copy(
                        update={"status": "skipped", "reason": "media_only_hold"}
                    ),
                )
            return
        conflicts = [
            s for s in self.store.steps() if s.active and s.resource == step.resource
        ]
        for conflict in conflicts:
            if conflict.priority >= step.priority:
                return
            self.cancel(conflict.event_id, "preempted")
        self._dispatch(step, now)

    def _dispatch(self, step: Step, now: int) -> None:
        """Consume the lease durably before crossing the output fault boundary."""
        previous = self.adapter.snapshot(step.resource)
        if not self.store.reserve(step, previous):
            return
        reserved = next(s for s in self.store.steps() if s.owner == step.owner)
        dispatched = reserved.model_copy(
            update={"status": "dispatched", "end_ms": now + step.cue.effect.duration_ms}
        )
        if self.store.transition(reserved, dispatched):
            # Durable consumption precedes the external call. Exceptions propagate;
            # recovery consumes the unknown result instead of retrying it.
            try:
                self.adapter.dispatch(
                    Dispatch(
                        owner=step.owner,
                        cue=step.cue,
                        resource=step.resource,
                        previous=previous,
                        deadline_ms=step.deadline_ms,
                    )
                )
            except AdapterFaultError:
                self.cancel(step.event_id, "adapter_fault")
                raise
