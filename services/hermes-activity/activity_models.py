"""Typed public activity and internal reduction values."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from hermes_feed import SpoolEvent

TimelineStatus = Literal["ok", "error", "running"]
ScreenKind = Literal["live", "shuttered", "offline"]


class TimelineEntry(BaseModel):
    """One bounded activity item in the public timeline."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    age_s: int = Field(ge=0, le=86_400)
    category: str = Field(min_length=1, max_length=12)
    action: str = Field(min_length=1, max_length=48)
    detail: str = Field(max_length=60)
    status: TimelineStatus
    event_ts_ms: int = Field(default=0, ge=0, exclude=True)


class ScreenState(BaseModel):
    """Validated screen metadata consumed by the Godot reader."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, populate_by_name=True)

    state: ScreenKind
    filename: str = Field(pattern=r"^hermes-screen-[01]\.jpg$")
    seq: int = Field(ge=0)
    width: int = Field(ge=1, le=1280)
    height: int = Field(ge=1, le=800)
    captured_at_ms: int = Field(ge=0)
    ttl_ms: int = Field(default=2_000, ge=1, le=2_000, serialization_alias="ttlMs")


class ActivityPayload(BaseModel):
    """Publicly safe activity projection."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    title: str = Field(min_length=1, max_length=180)
    summary: str = Field(max_length=180)
    status: str = Field(min_length=1, max_length=24)
    tool: str = Field(min_length=1, max_length=12)
    timeline: tuple[TimelineEntry, ...] = Field(max_length=6)
    screen: ScreenState


class ActivityEvent(BaseModel):
    """Godot-compatible character activity event."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, serialize_by_alias=True, populate_by_name=True)

    schema_version: Literal["furbomek.character.v1"] = Field(
        default="furbomek.character.v1", serialization_alias="schemaVersion", validation_alias="schemaVersion"
    )
    kind: Literal["agent.activity"] = "agent.activity"
    source: Literal["hermes-adapter"] = "hermes-adapter"
    audience: Literal["public"] = "public"
    sensitivity: Literal["public"] = "public"
    seq: int = Field(ge=0)
    observed_at: str = Field(
        serialization_alias="observedAt",
        validation_alias="observedAt",
        pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$",
    )
    ttl_ms: int = Field(default=5_000, ge=1, le=30_000, serialization_alias="ttlMs", validation_alias="ttlMs")
    payload: ActivityPayload


@dataclass(frozen=True, slots=True)
class BrokerState:
    """Immutable reduction state retained by the broker checkpoint."""

    seq: int
    phase: str
    title: str
    summary: str
    tool: str
    timeline: tuple[TimelineEntry, ...]
    shutter: bool
    session_open: bool
    last_event_ms: int

    @classmethod
    def initial(cls, now_ms: int) -> BrokerState:
        """Build the safe initial public state."""
        return cls(
            seq=0,
            phase="idle",
            title="Awaiting activity",
            summary="No Hermes events yet",
            tool="AGENT",
            timeline=(),
            shutter=True,
            session_open=False,
            last_event_ms=now_ms,
        )


def event_time(event: SpoolEvent, fallback_ms: int) -> int:
    """Use the producer timestamp and only fall back for impossible zero values."""
    return event.ts_ms if event.ts_ms > 0 else fallback_ms
