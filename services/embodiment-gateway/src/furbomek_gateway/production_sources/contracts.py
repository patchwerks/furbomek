"""Typed, private source results and operator-owned admission policy."""

from typing import Annotated, Literal, NoReturn

from pydantic import Field

from furbomek_gateway.effect_contracts import Contract, Identifier
from furbomek_gateway.reaction_contracts import PrivateEvent

Intent = Literal["acknowledge", "rgb", "xyz", "liquidation"]
Reason = Literal[
    "disabled",
    "origin",
    "malformed",
    "stale",
    "scope",
    "moderation",
    "intent",
    "duplicate",
    "rate",
    "snapshot",
    "control",
    "untimed",
    "revoked",
    "capacity",
]


class RatePolicy(Contract):
    """Explicit caps; live enrollment requires a measured-load evidence reference."""

    source_per_minute: Annotated[int, Field(ge=1, le=1000)]
    user_per_minute: Annotated[int, Field(ge=1, le=100)]
    load_evidence: Identifier


class SourcePolicy(Contract):
    """Operator-local identity, kill switch and freshness bounds."""

    enabled: bool = False
    adapter_id: Identifier
    scope: Identifier
    session_id: Identifier
    rate: RatePolicy
    max_age_ms: Annotated[int, Field(ge=1, le=10000)] = 10000


class SourceReceipt(Contract):
    """Private event plus curated intent; no tool or motion permission fields."""

    status: Literal["accepted"] = "accepted"
    event: PrivateEvent
    intent: Intent
    preview: Literal["Audience preset requested", "Liquidation observed"]


class SourceDisposition(Contract):
    """Redacted denial or transport observation, never an actionable receipt."""

    status: Literal["denied", "observed"]
    reason: Reason


SourceResult = SourceReceipt | SourceDisposition


class SourceRejectedError(Exception):
    """Boundary rejection whose reason contains no provider data."""

    def __init__(self, reason: Reason) -> None:
        """Carry only the closed rejection reason."""
        self.reason: Reason = reason
        super().__init__(reason)


def reject(reason: Reason) -> NoReturn:
    """Raise a redacted typed admission error."""
    raise SourceRejectedError(reason)
