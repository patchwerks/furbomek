"""Closed production socket requests and transport-bound curated source routing."""

from typing import Annotated, Literal

from pydantic import Field

from .edge_time import CLOCK_SKEW_MS, REQUEST_AGE_MS, unix_ms
from .effect_contracts import CAPABILITIES, CapabilityDefinition, Contract, Identifier
from .motion_sequence_models import SequenceRequest
from .production_http_models import OwnerAction, OwnerResult, OwnerState
from .production_sources.contracts import SourceReceipt
from .reaction_contracts import ReactionPack
from .reaction_types import Projection


class Status(Contract):
    """Read current state and the same reviewed catalog used by the studio."""

    command: Literal["status"] = "status"


class OwnerOperation(Contract):
    """Typed authoring command; no shell, asset path or physical permit."""

    command: Literal["owner"] = "owner"
    request: OwnerAction


class ReactionOperation(Contract):
    """Only private configured pack identifiers are selectable."""

    command: Literal["reaction"] = "reaction"
    action: Literal["preview", "trigger", "cancel", "status"]
    pack: Identifier | None = None
    event_id: Annotated[int, Field(ge=1)] | None = None


class SourceDelivery(Contract):
    """Source claims are checked against the authenticated socket binding."""

    command: Literal["source"] = "source"
    receipt: SourceReceipt


class PresetApply(Contract):
    """Apply previously saved typed values using the current owner revision."""

    command: Literal["preset"] = "preset"
    epoch: Identifier
    revision: Annotated[int, Field(ge=0)]


class Movement(Contract):
    """Bounded intent remains HOLD without an independently issued local permit."""

    command: Literal["movement"] = "movement"
    request: SequenceRequest


Operation = Annotated[
    Status
    | OwnerOperation
    | ReactionOperation
    | SourceDelivery
    | PresetApply
    | Movement,
    Field(discriminator="command"),
]


class ProductionRequest(Contract):
    """Single bounded semantic socket envelope."""

    target: Literal["production"] = "production"
    issued_ms: Annotated[int, Field(ge=0)]
    operation: Operation

    def fresh(self) -> bool:
        """Use the legacy edge's same freshness fence."""
        return -CLOCK_SKEW_MS <= unix_ms() - self.issued_ms <= REQUEST_AGE_MS


class ProductionReply(Contract):
    """Only sanitized owner state and scheduler projection leave the controller."""

    state: OwnerState
    stage: Literal["HOLD"] = "HOLD"
    stage_reason: Literal["no_authenticated_production_release"] = (
        "no_authenticated_production_release"
    )
    catalog: tuple[CapabilityDefinition, ...] = CAPABILITIES
    result: OwnerResult | None = None
    reactions: tuple[Projection, ...] = ()
    pack: ReactionPack | None = None
    event_id: int | None = None
    accepted: bool = True
    reason: Literal[
        "observed",
        "previewed",
        "submitted",
        "cancelled",
        "held",
        "origin",
        "unknown_pack",
        "duplicate",
        "stale",
    ] = "observed"
