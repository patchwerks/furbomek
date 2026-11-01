"""Typed, bounded Hermes activity spool records."""

from __future__ import annotations

import os
from pathlib import Path
from typing import ClassVar, Final, Literal

from pydantic import BaseModel, ConfigDict, Field

from character_state import CharacterInput  # noqa: TC001 - Pydantic resolves this field at runtime.

SpoolKind = Literal["session_start", "session_end", "thinking", "turn_done", "tool", "approval", "character"]
SpoolPhase = Literal["running", "ok", "error", "waiting", "resolved", "interrupted"]
SpoolCategory = Literal["BROWSER", "COMPUTER", "WEB", "TERMINAL", "FILES", "AGENT"]
MAX_LINE_BYTES: Final = 4_096


class SpoolEvent(BaseModel):
    """One producer event accepted by the broker boundary."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="ignore")

    v: Literal[1] = 1
    kind: SpoolKind
    ts_ms: int = Field(ge=0)
    session: str = Field(max_length=64)
    phase: SpoolPhase = "ok"
    category: SpoolCategory = "AGENT"
    action: str = Field(min_length=1, max_length=48)
    detail: str = Field(max_length=60)
    shutter: bool = False
    duration_ms: int = Field(default=0, ge=0, le=86_400_000)
    call: str = Field(default="", max_length=64)
    privacy_release: bool = False
    character: CharacterInput | None = None


def parse_complete_line(line: bytes, *, strict: bool = False) -> SpoolEvent | None:
    """Parse one newline-terminated record, rejecting malformed input."""
    if len(line) > MAX_LINE_BYTES or not line.endswith(b"\n"):
        return None
    try:
        event = SpoolEvent.model_validate_json(line, strict=strict)
    except (UnicodeDecodeError, ValueError):
        return None
    if event.kind == "character" and event.character is None:
        return None
    if event.phase == "interrupted" and event.kind != "session_end":
        return None
    if strict and not _valid_phase(event):
        return None
    return event


def _valid_phase(event: SpoolEvent) -> bool:
    phases: dict[str, set[str]] = {
        "session_start": {"ok"},
        "thinking": {"ok"},
        "turn_done": {"ok"},
        "session_end": {"ok", "error", "interrupted"},
        "tool": {"running", "ok", "error"},
        "approval": {"waiting", "resolved"},
    }
    return event.kind == "character" or event.phase in phases[event.kind]


def spool_directory() -> Path:
    """Return the owner-only default spool directory."""
    configured = os.environ.get("FURBOMEK_ACTIVITY_SPOOL")
    if configured:
        return Path(configured)
    return Path(f"/dev/shm/furbomek-hermes-{os.getuid()}")
