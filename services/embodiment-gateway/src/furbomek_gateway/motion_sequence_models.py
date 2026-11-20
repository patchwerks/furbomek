"""Bounded sequence requests and explicitly non-physical offline receipts."""

from typing import Annotated, Literal, Protocol

from pydantic import Field

from furbomek_gateway.guard_models import ActionName, PoweredActionResult
from furbomek_gateway.motion_geometry import Contract, Identifier
from furbomek_gateway.stage_models import StageReceipt, StageRequest


class SequenceStep(Contract):
    """Exact selected portable profile and semantic verb."""

    profile_id: Identifier
    action: ActionName


class SequenceRequest(Contract):
    """One finite queue, with no authority-bearing caller fields."""

    steps: Annotated[tuple[SequenceStep, ...], Field(min_length=1, max_length=8)]
    duration_ms: Annotated[int, Field(gt=0, le=30000, strict=True)]


class OfflineQualification(Contract):
    """Locally injected PTY comparison selection; never a production permit."""

    enabled: bool = False
    profile_ids: tuple[Identifier, ...] = ()
    transitions: tuple[tuple[Identifier, Identifier], ...] = ()
    valid_from_ms: Annotated[int, Field(ge=0, strict=True)]
    valid_until_ms: Annotated[int, Field(ge=0, strict=True)]


class StepVerdict(Contract):
    """Guard wire facts and independent observation stay separate."""

    stage: StageReceipt
    guard: PoweredActionResult | None = None
    optical: Literal["pass", "fail", "uncertain"] = "uncertain"


class SequenceResult(Contract):
    """A PTY completion cannot imply physical movement or release."""

    status: Literal["completed", "HOLD", "cancelled", "uncertain"]
    reason: str
    steps: tuple[StepVerdict, ...] = ()
    physical_motion_authorized: Literal[False] = False
    physical_motor_state: Literal["unknown"] = "unknown"


class SequenceObserver(Protocol):
    """Trusted local observation source, outside any model-supplied request."""

    def before_step(self, step: SequenceStep, /) -> StageRequest:
        """Return current stage, pose, profile and stopping envelope evidence."""
        ...

    def after_step(self, step: SequenceStep, /) -> Literal["pass", "fail", "uncertain"]:
        """Evaluate the observed outcome independently of wire success."""
        ...
