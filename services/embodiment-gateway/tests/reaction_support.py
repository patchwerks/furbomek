"""Test-only virtual clock and CAS renderer; never imported by runtime."""

from typing import final

from furbomek_gateway.effect_contracts import AppliedAck, Resource
from furbomek_gateway.reaction_types import AdapterFaultError, Dispatch, PropertyState


@final
class Clock:
    """Mutable virtual time controlled by each isolated scenario."""

    def __init__(self) -> None:
        self.now = 0

    def monotonic_ms(self) -> int:
        return self.now

    def epoch_ms(self) -> int:
        return 1000 + self.now


@final
class Adapter:
    """Mutable test-only renderer state implementing actual lease CAS semantics."""

    def __init__(self) -> None:
        self.states: dict[Resource, PropertyState] = {}
        self.requests: list[Dispatch] = []
        self.ready = True
        self.fault = False
        self.stops = 0

    def available(self, resource: Resource) -> bool:
        return self.ready and resource in (
            "hud",
            "graphics",
            "sfx",
            "robot",
            "face",
            "voice",
        )

    def snapshot(self, resource: Resource) -> PropertyState:
        return self.states.get(resource, PropertyState(resource=resource, revision=0))

    def dispatch(self, request: Dispatch) -> None:
        current = self.snapshot(request.resource)
        if current.revision == request.previous.revision:
            self.states[request.resource] = PropertyState(
                resource=request.resource,
                owner=request.owner,
                revision=current.revision + 1,
                effect=request.cue.effect,
            )
            self.requests.append(request)
            if self.fault:
                raise AdapterFaultError(request.resource)

    def release(self, state: PropertyState, previous: PropertyState | None) -> bool:
        if self.snapshot(state.resource) != state:
            return False
        self.states[state.resource] = PropertyState(
            resource=state.resource,
            revision=state.revision + 1,
            effect=previous.effect if previous else None,
        )
        return True

    def stop(self) -> None:
        self.stops += 1

    def ack(self, request: Dispatch) -> AppliedAck:
        state = self.snapshot(request.resource)
        return AppliedAck(
            status="applied",
            cue_id=request.cue.id,
            capability=request.cue.effect.capability,
            resource=request.resource,
            owner=request.owner,
            previous_revision=request.previous.revision,
            revision=state.revision,
            effective=request.cue.effect,
            available=True,
        )
