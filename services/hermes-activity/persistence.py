"""Atomic broker, privacy, cursor, and publication checkpoints."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from activity_models import BrokerState, TimelineEntry, TimelineStatus
from cursor import CursorSnapshot
from privacy import HoldKey, PrivacyState


class TimelineCheckpoint(BaseModel):
    """Durable timeline row."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    age_s: int = Field(ge=0, le=86_400)
    category: str = Field(min_length=1, max_length=12)
    action: str = Field(min_length=1, max_length=48)
    detail: str = Field(max_length=60)
    status: TimelineStatus
    event_ts_ms: int = Field(ge=0)


class BrokerCheckpoint(BaseModel):
    """Durable broker reduction fields."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    phase: str
    title: str
    summary: str
    tool: str
    timeline: tuple[TimelineCheckpoint, ...]
    shutter: bool
    session_open: bool
    last_event_ms: int


class HoldCheckpoint(BaseModel):
    """Durable privacy hold key."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    session: str
    call: str


class PrivacyCheckpoint(BaseModel):
    """Durable privacy latch fields."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    latched: bool
    uncertain: bool
    release_requested: bool
    generation_required: bool
    fresh_generation: bool
    fresh_capture_required: bool
    generation: str | None
    holds: tuple[HoldCheckpoint, ...]


class Checkpoint(BaseModel):
    """Atomic runtime checkpoint document."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    version: int = Field(default=1, ge=1, le=1)
    cursor_inode: int | None
    cursor_offset: int = Field(ge=0)
    publication_seq: int = Field(ge=0)
    screen_seq: int = Field(ge=0)
    broker: BrokerCheckpoint
    privacy: PrivacyCheckpoint


@dataclass(frozen=True, slots=True)
class RuntimeSnapshot:
    """In-memory values written as one checkpoint."""

    cursor: CursorSnapshot
    broker: BrokerState
    privacy: PrivacyState
    publication_seq: int
    screen_seq: int


def load_checkpoint(path: Path) -> Checkpoint | None:
    """Load a checkpoint only when its complete typed document is valid."""
    try:
        return Checkpoint.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        return None


def save_checkpoint(path: Path, snapshot: RuntimeSnapshot) -> None:
    """Atomically replace the single durable runtime checkpoint."""
    checkpoint = _checkpoint(snapshot)
    pending = path.with_name(f".{path.name}.{os.getpid()}.pending")
    pending.write_text(checkpoint.model_dump_json(), encoding="utf-8")
    pending.replace(path)


def restore_snapshot(checkpoint: Checkpoint) -> RuntimeSnapshot:
    """Rebuild typed runtime values from a validated checkpoint."""
    timeline = tuple(
        TimelineEntry(
            age_s=item.age_s,
            category=item.category,
            action=item.action,
            detail=item.detail,
            status=item.status,
            event_ts_ms=item.event_ts_ms,
        )
        for item in checkpoint.broker.timeline
    )
    broker = BrokerState(
        checkpoint.publication_seq,
        checkpoint.broker.phase,
        checkpoint.broker.title,
        checkpoint.broker.summary,
        checkpoint.broker.tool,
        timeline,
        checkpoint.broker.shutter,
        checkpoint.broker.session_open,
        checkpoint.broker.last_event_ms,
    )
    privacy = PrivacyState(
        checkpoint.privacy.latched,
        checkpoint.privacy.uncertain,
        checkpoint.privacy.release_requested,
        checkpoint.privacy.generation_required,
        checkpoint.privacy.fresh_generation,
        checkpoint.privacy.fresh_capture_required,
        checkpoint.privacy.generation,
        frozenset(HoldKey(item.session, item.call) for item in checkpoint.privacy.holds),
    )
    return RuntimeSnapshot(
        CursorSnapshot(checkpoint.cursor_inode, checkpoint.cursor_offset),
        broker,
        privacy,
        checkpoint.publication_seq,
        checkpoint.screen_seq,
    )


def published_sequences(out_dir: Path) -> tuple[int, int]:
    """Seed publication and screen sequences from an existing output."""
    try:
        raw = (out_dir / "activity.json").read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return 0, 0
    publication = _number(raw, r'"seq"\s*:\s*(\d+)')
    screen = _number(raw, r'"screen"\s*:\s*\{[^{}]*"seq"\s*:\s*(\d+)')
    return publication, screen


def _checkpoint(snapshot: RuntimeSnapshot) -> Checkpoint:
    broker = BrokerCheckpoint(
        phase=snapshot.broker.phase,
        title=snapshot.broker.title,
        summary=snapshot.broker.summary,
        tool=snapshot.broker.tool,
        timeline=tuple(
            TimelineCheckpoint(
                age_s=item.age_s,
                category=item.category,
                action=item.action,
                detail=item.detail,
                status=item.status,
                event_ts_ms=item.event_ts_ms,
            )
            for item in snapshot.broker.timeline
        ),
        shutter=snapshot.broker.shutter,
        session_open=snapshot.broker.session_open,
        last_event_ms=snapshot.broker.last_event_ms,
    )
    privacy = PrivacyCheckpoint(
        latched=snapshot.privacy.latched,
        uncertain=snapshot.privacy.uncertain,
        release_requested=snapshot.privacy.release_requested,
        generation_required=snapshot.privacy.generation_required,
        fresh_generation=snapshot.privacy.fresh_generation,
        fresh_capture_required=snapshot.privacy.fresh_capture_required,
        generation=snapshot.privacy.generation,
        holds=tuple(HoldCheckpoint(session=item.session, call=item.call) for item in snapshot.privacy.holds),
    )
    return Checkpoint(
        cursor_inode=snapshot.cursor.inode,
        cursor_offset=snapshot.cursor.offset,
        publication_seq=snapshot.publication_seq,
        screen_seq=snapshot.screen_seq,
        broker=broker,
        privacy=privacy,
    )


def _number(raw: str, pattern: str) -> int:
    match = re.search(pattern, raw)
    return int(match.group(1)) if match is not None else 0
