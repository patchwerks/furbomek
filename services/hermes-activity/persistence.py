"""Atomic broker, privacy, cursor, and publication checkpoints."""

from __future__ import annotations

import os
import re
import stat
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar, Self

if TYPE_CHECKING:
    from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, model_validator

from activity_models import BrokerState, TimelineEntry, TimelineStatus
from character_state import CharacterState
from cursor import CursorSnapshot
from privacy import HoldKey, PrivacyState

MAX_CHECKPOINT_BYTES = 262_144


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
    character: CharacterState | None = None

    @model_validator(mode="after")
    def require_complete_character(self, info: ValidationInfo) -> Self:
        """Reject persisted authority that reconstructs missing cancellation fields from defaults."""
        if (
            info.mode == "json"
            and self.character is not None
            and self.character.model_fields_set != set(CharacterState.model_fields)
        ):
            msg = "persisted character state requires every authority field"
            raise ValueError(msg)
        return self


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

    version: int = Field(default=2, ge=1, le=2)
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
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(descriptor, "rb") as stream:
            metadata = os.fstat(stream.fileno())
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid() or metadata.st_mode & 0o022:
                return None
            raw = stream.read(MAX_CHECKPOINT_BYTES + 1)
        if len(raw) > MAX_CHECKPOINT_BYTES:
            return None
        return Checkpoint.model_validate_json(raw)
    except (OSError, UnicodeDecodeError, ValueError):
        return None


def save_checkpoint(path: Path, snapshot: RuntimeSnapshot) -> None:
    """Atomically replace the single durable runtime checkpoint."""
    checkpoint = _checkpoint(snapshot)
    pending = path.with_name(f".{path.name}.{os.getpid()}.pending")
    descriptor = os.open(pending, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        os.fchmod(stream.fileno(), 0o600)
        stream.write(checkpoint.model_dump_json())
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
        checkpoint.broker.character,
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
        character=snapshot.broker.character,
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
