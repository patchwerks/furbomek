"""Bounded direct owner effects and actual consumer lease restoration."""

import time
from typing import Final, Literal, final
from uuid import uuid4

from pydantic import ValidationError

from .effect_contracts import AppliedAck, GraphicsEffect, capability_definition
from .production_http_models import EffectRequest, VisualRequest
from .production_media import ProductionMedia
from .reaction_contracts import Cue
from .reaction_types import (
    AdapterFaultError,
    Clock,
    Dispatch,
    PropertyState,
    StorePrivacyError,
)

EffectOutcome = Literal[
    "applied", "held", "stale", "unavailable", "reverted", "cancelled"
]


NEUTRAL: Final = GraphicsEffect(
    capability="graphics.pulse.v1",
    preset="neutral",
    intensity_percent=0,
    duration_ms=30000,
)


@final
class EffectOwner:
    """Mutable exact ownership for one serialized controller; no default engine."""

    def __init__(self, media: ProductionMedia, clock: Clock) -> None:
        """Start without a live lease, regardless of any persisted configuration."""
        self.media = media
        self.clock = clock
        self.revision = 0
        self.owner_until_ms = 0
        self.last_ack: AppliedAck | None = None
        self.previous: PropertyState | None = None
        self.current: PropertyState | None = None

    def apply(self, request: EffectRequest) -> EffectOutcome:
        """Dispatch once and require the exact fresh consumer ACK."""
        resource = capability_definition(request.effect.capability).resource
        if not self.media.available(resource):
            return "unavailable"
        previous = self.media.snapshot(resource)
        owner = uuid4().hex
        cue = Cue(
            id=owner,
            after=(),
            effect=request.effect,
            condition="capability_available",
            ttl_ms=request.effect.duration_ms,
            on_unavailable="cancel_pack",
            on_fault="cancel_pack",
        )
        self.revision += 1
        self.media.dispatch(
            Dispatch(
                owner=owner,
                cue=cue,
                resource=resource,
                previous=previous,
                deadline_ms=self.clock.monotonic_ms() + request.effect.duration_ms,
            )
        )
        deadline = time.monotonic() + 0.5
        while time.monotonic() < deadline:
            ack = self.media.acknowledge(owner)
            if ack is not None:
                self.owner_until_ms = (
                    self.clock.monotonic_ms() + request.effect.duration_ms
                )
                self.previous, self.current, self.last_ack = (
                    previous,
                    self.media.snapshot(resource),
                    ack,
                )
                return "applied"
            time.sleep(0.01)
        # An uncertain outcome is never retried or promoted to applied.
        self.media.stop()
        return "held"

    def visual(self, request: VisualRequest) -> EffectOutcome:
        """Apply bounded visual settings and await actual application."""
        previous = self.media.snapshot("graphics")
        self.revision += 1
        owner = self.media.apply_visual(
            request.visual, previous, duration_ms=request.duration_ms
        )
        deadline = time.monotonic() + 0.5
        while time.monotonic() < deadline:
            receipt = self.media.visual_receipt(owner)
            if receipt is not None:
                self.owner_until_ms = self.clock.monotonic_ms() + request.duration_ms
                self.previous, self.current = previous, self.media.snapshot("graphics")
                self.last_ack = None
                return "applied"
            time.sleep(0.01)
        self.media.stop()
        return "held"

    def release(self, *, restore: bool) -> EffectOutcome:
        """Restore only an unchanged observed lease, never another writer."""
        if self.current is None:
            return "held"
        try:
            if self.media.snapshot(self.current.resource) != self.current:
                return "stale"
            self.revision += 1
            if not self.media.release(self.current, self.previous if restore else None):
                return "held"
        except (OSError, ValidationError, AdapterFaultError, StorePrivacyError):
            return "unavailable"
        self.current = self.previous = self.last_ack = None
        return "reverted" if restore else "cancelled"
