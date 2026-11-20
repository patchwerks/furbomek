"""Private scheduler values and adapter obligations; no production backend."""

from dataclasses import dataclass
from enum import IntEnum
from time import monotonic_ns, time_ns
from typing import Literal, Protocol, assert_never, override

from .effect_contracts import AppliedAck, Contract, Effect, Resource
from .reaction_contracts import Cue

StepStatus = Literal[
    "pending",
    "reserved",
    "dispatched",
    "applied",
    "completed",
    "skipped",
    "expired",
    "cancelled",
    "uncertain",
]


class Priority(IntEnum):
    """Local authority only; STOP bypasses arbitration entirely."""

    CURATED = 0
    ADMITTED = 1
    OWNER = 2


class PropertyState(Contract):
    """Actual renderer snapshot; revision increases even for same-value edits."""

    resource: Resource
    owner: str | None = None
    revision: int
    effect: Effect | None = None


class Reservation(Contract):
    """Admission timing anchored once to the local monotonic clock."""

    now_ms: int
    age_budget_ms: int
    priority: Priority


class Step(Contract):
    """Durable private step journal; owner is a unique dispatch token."""

    owner: str
    event_id: int
    ordinal: int
    cue: Cue
    resource: Resource
    priority: Priority
    due_ms: int
    deadline_ms: int
    status: StepStatus = "pending"
    reason: str = ""
    previous: PropertyState | None = None
    ack: AppliedAck | None = None
    end_ms: int | None = None

    @property
    def active(self) -> bool:
        """Whether this step owns a resource or may have caused an output."""
        match self.status:
            case "reserved" | "dispatched" | "applied":
                return True
            case (
                "pending"
                | "completed"
                | "skipped"
                | "expired"
                | "cancelled"
                | "uncertain"
            ):
                return False
            case _:
                assert_never(self.status)


class Dispatch(Contract):
    """A bounded CAS request, never an arbitrary tool or actuator command."""

    owner: str
    cue: Cue
    resource: Resource
    previous: PropertyState
    deadline_ms: int


class Clock(Protocol):
    """Epoch used only for fresh admission; all cue timing is monotonic."""

    def monotonic_ms(self) -> int:
        """Return the monotonic scheduling timestamp."""
        ...

    def epoch_ms(self) -> int:
        """Return epoch time for source freshness."""
        ...


class HostClock:
    """Single host clock domain; interrupted schedules never resume on restart."""

    def monotonic_ms(self) -> int:
        """Return local monotonic milliseconds."""
        return monotonic_ns() // 1_000_000

    def epoch_ms(self) -> int:
        """Return epoch milliseconds for event-age verification."""
        return time_ns() // 1_000_000


class ReactionAdapter(Protocol):
    """Trusted local consumer, installed separately by the integration owner.

    Dispatch MUST atomically compare previous revision, apply once per owner,
    and return its eventual AppliedAck to acknowledge(). Release MUST CAS the
    entire owner/revision and restore only the supplied value (None = neutral).
    Manual changes increment revision AND revoke owner even if value is equal.
    Stop MUST be unconditional/idempotent and cancel any in-flight physical work.
    Methods must be bounded; local hardware watchdogs remain independently owned.
    """

    def available(self, resource: Resource) -> bool:
        """Read current local capability availability."""
        ...

    def snapshot(self, resource: Resource) -> PropertyState:
        """Read actual current property owner, value and revision."""
        ...

    def dispatch(self, request: Dispatch) -> None:
        """Apply once with revision CAS; report an actual ACK later."""
        ...

    def release(self, state: PropertyState, previous: PropertyState | None) -> bool:
        """CAS the current lease to previous value or neutral."""
        ...

    def stop(self) -> None:
        """Stop physical work unconditionally, including in-flight requests."""
        ...


@dataclass(frozen=True, slots=True)
class StorePrivacyError(RuntimeError):
    """Refuse a non-private store rather than changing an unrelated directory."""

    path: str

    @override
    def __str__(self) -> str:
        """Describe the rejected private state path."""
        return f"private owner-only store required: {self.path}"


class Projection(Contract):
    """Read-only observer view; no identities, arbitrary text or authority."""

    resource: Resource
    status: StepStatus
    media_only_hold: bool


@dataclass(frozen=True, slots=True)
class AdapterFaultError(RuntimeError):
    """Typed local dispatch failure; uncertainty must never trigger retry."""

    resource: Resource

    @override
    def __str__(self) -> str:
        """Describe the failed output without provider text."""
        return f"reaction adapter fault: {self.resource}"
