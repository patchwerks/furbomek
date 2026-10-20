"""Typed, bounded Hermes activity spool records."""

from __future__ import annotations

import os
from pathlib import Path
from typing import ClassVar, Final, Literal

from pydantic import BaseModel, ConfigDict, Field

SpoolKind = Literal["session_start", "session_end", "thinking", "turn_done", "tool", "approval"]
SpoolPhase = Literal["running", "ok", "error", "waiting", "resolved"]
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


def parse_complete_line(line: bytes) -> SpoolEvent | None:
    """Parse one newline-terminated record, rejecting malformed input."""
    if len(line) > MAX_LINE_BYTES or not line.endswith(b"\n"):
        return None
    try:
        return SpoolEvent.model_validate_json(line)
    except (UnicodeDecodeError, ValueError):
        return None


def spool_directory() -> Path:
    """Return the owner-only default spool directory."""
    configured = os.environ.get("FURBOMEK_ACTIVITY_SPOOL")
    if configured:
        return Path(configured)
    return Path(f"/dev/shm/furbomek-hermes-{os.getuid()}")
