"""Closed owner HTTP DTOs; controller state is the sole observation authority."""

from typing import Annotated, Literal, Protocol

from pydantic import Field, TypeAdapter

from .effect_contracts import (
    AppliedAck,
    Contract,
    GraphicsEffect,
    HudEffect,
    Identifier,
    SfxEffect,
)
from .framing_models import FramingPreset, Manual
from .production_media_contracts import VisualSettings

SafeEffect = Annotated[
    GraphicsEffect | HudEffect | SfxEffect, Field(discriminator="capability")
]
Revision = Annotated[int, Field(ge=0)]


class OwnerSaved(Contract):
    """Owner-safe preset; no executable cue or physical authority."""

    effect: SafeEffect
    framing: FramingPreset | None = None


class OwnerState(Contract):
    """Only observed applied effects belong here; unavailable starts null."""

    mode: Literal["live"] = "live"
    origin: Literal["controller", "injected-test-fixture"]
    owner: Literal["local-owner"] = "local-owner"
    epoch: Identifier
    revision: Revision
    health: Literal["fresh", "held", "unavailable"]
    applied: SafeEffect | None = None
    previous: SafeEffect | None = None
    saved: OwnerSaved | None = None
    framing: FramingPreset | None = None
    receipt: AppliedAck | None = None
    visual: VisualSettings | None = None
    visual_available: bool = False
    framing_available: bool = False
    reason: Literal["observed", "held", "unavailable", "unsupported"] = "unavailable"


class RevisionRequest(Contract):
    """Optimistic concurrency shared with all other controller writers."""

    epoch: Identifier
    revision: Revision


class EffectRequest(RevisionRequest):
    """Bounded safe effect preview or apply."""

    action: Literal["preview", "apply"]
    effect: SafeEffect


class SaveRequest(RevisionRequest):
    """Persist typed authoring configuration without dispatch."""

    action: Literal["save"]
    saved: OwnerSaved


class SimpleRequest(RevisionRequest):
    """Closed commands; no operational admission, paths or navigation."""

    action: Literal["revert", "cancel"]


class FramingRequest(RevisionRequest):
    """Validated versioned framing configuration for the owning controller."""

    action: Literal["framing-preview", "framing-apply", "framing-save"]
    framing: FramingPreset


class VisualRequest(RevisionRequest):
    """Safe visual settings without renderer mailbox authority."""

    action: Literal["visual-preview", "visual-apply"]
    visual: VisualSettings
    duration_ms: Annotated[int, Field(ge=1, le=30000)]


class ManualRequest(RevisionRequest):
    """Bounded owner framing override, never physical admission."""

    action: Literal["framing-manual"]
    manual: Manual


OwnerAction = Annotated[
    EffectRequest
    | SaveRequest
    | SimpleRequest
    | FramingRequest
    | VisualRequest
    | ManualRequest,
    Field(discriminator="action"),
]
ACTION = TypeAdapter(OwnerAction)


class OwnerResult(Contract):
    """Controller receipt, including refusals; transport never invents success."""

    outcome: Literal["accepted", "rejected"]
    reason: Literal[
        "previewed",
        "applied",
        "saved",
        "cancelled",
        "reverted",
        "held",
        "unavailable",
        "stale",
        "busy",
        "unsupported",
    ]
    state: OwnerState
    preview: SafeEffect | None = None
    framing_preview: FramingPreset | None = None
    visual_preview: VisualSettings | None = None


class ProductionController(Protocol):
    """Task14 injects its real orchestrator; there is no default implementation.

    Execute MUST atomically check epoch/revision against every writer, including
    MCP. Accepted apply/revert must return observed state and genuine downstream
    receipts. Save/preview confer no dispatch authority. Status must expire stale
    observations to held/unavailable. Preview/save are non-dispatch and may
    validate under HOLD; cancel affects only locally owned work. HTTP's lock
    covers only this transport.
    """

    def status(self) -> OwnerState:
        """Read the current observed state without mutation."""
        ...

    def execute(self, request: OwnerAction) -> OwnerResult:
        """Execute one typed operation; gate dispatch and scoped cancellation."""
        ...
