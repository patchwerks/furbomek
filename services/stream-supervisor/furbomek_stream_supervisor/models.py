"""Configuration, paths, worker definitions, and health contracts."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import ClassVar, Final, Literal

from pydantic import BaseModel, ConfigDict, Field


class ScreenPolicy(StrEnum):
    """Select whether the activity broker may use a dedicated Hermes desktop."""

    OFF = "off"
    BOT_DESKTOP = "bot-desktop"


class HealthState(StrEnum):
    """Lifecycle state written to the owner-only health document."""

    STARTING = "starting"
    READY = "ready"
    DEGRADED = "degraded"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"


class WorkerStatus(StrEnum):
    """Status of one supervised child."""

    NOT_STARTED = "not_started"
    STARTING = "starting"
    RUNNING = "running"
    BACKOFF = "backoff"
    EXITED = "exited"
    STOPPED = "stopped"
    FAILED = "failed"


class RuntimeSettings(BaseModel):
    """Owner-authored runtime settings accepted by the supervisor."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid", strict=True)

    schema_version: Literal[1] = 1
    record: bool = False
    screen_policy: ScreenPolicy = ScreenPolicy.OFF
    readiness_timeout_s: int = Field(default=30, ge=1, le=300)


class BotDesktopRuntime(BaseModel):
    """Validated environment published by a dedicated Hermes desktop."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid", strict=True)

    display: str = Field(min_length=1)
    xauthority: Path
    pid: int = Field(gt=0)
    generation: str = Field(min_length=1)


class TrackingReadiness(BaseModel):
    """Minimum tracking fields needed to prove a fresh producer contract."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore", strict=True)

    schema_version: Literal["furbomek.vision.v1"] = Field(alias="schema")
    sequence: int = Field(ge=1)
    capture_monotonic_ns: int = Field(ge=0)
    produced_monotonic_ns: int = Field(ge=0)
    produced_unix_ms: int = Field(ge=0)
    frame_file: str = Field(pattern=r"^frame-[0-3]\.bin$")
    image_file: str = Field(pattern=r"^frame-[0-3]\.jpg\.bin$")
    optical_file: str = Field(pattern=r"^frame-[0-3]\.optical\.bin$")
    valid_points: int = Field(ge=0, le=217088)
    capture_fps: float = Field(ge=0)
    ttl_ms: int = Field(ge=1, le=30_000)


class ActivityPayloadReadiness(BaseModel):
    """Required public activity fields used by the renderer contract."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore", strict=True)

    title: str = Field(min_length=1, max_length=60)
    summary: str = Field(max_length=120)
    status: str = Field(min_length=1, max_length=24)
    tool: str = Field(min_length=1, max_length=12)


class ActivityReadiness(BaseModel):
    """Minimum activity fields needed to prove a fresh broker contract."""

    model_config: ClassVar[ConfigDict] = ConfigDict(
        extra="ignore", strict=True, populate_by_name=True
    )

    schema_version: Literal["furbomek.character.v1"] = Field(alias="schemaVersion")
    kind: Literal["agent.activity"]
    source: Literal["hermes-adapter", "a2ui-adapter", "glimpse-adapter"]
    audience: Literal["public"]
    sensitivity: Literal["public"]
    seq: int = Field(ge=0)
    observed_at: datetime = Field(alias="observedAt")
    ttl_ms: int = Field(alias="ttlMs", ge=1, le=30_000)
    payload: ActivityPayloadReadiness


@dataclass(frozen=True, slots=True)
class RuntimePaths:
    """Filesystem locations owned by one private media session."""

    repo: Path
    media_root: Path
    kinect_dir: Path
    hermes_profile: Path
    hermes_source: Path
    hermes_python: Path
    spool: Path

    @classmethod
    def from_environment(cls, repo: Path, env: Mapping[str, str]) -> RuntimePaths:
        """Resolve runtime paths without importing host-specific values."""
        uid = os.getuid()
        media_root = Path(env.get("FURBOMEK_MEDIA_ROOT", "/data/furbomek-media"))
        kinect_dir = Path(env.get("FURBOMEK_KINECT_DIR", f"/dev/shm/furbomek-kinect2-{uid}"))
        spool = Path(
            env.get("FURBOMEK_ACTIVITY_SPOOL", f"/dev/shm/furbomek-hermes-{uid}/events.jsonl")
        )
        return cls(
            repo=repo,
            media_root=media_root,
            kinect_dir=kinect_dir,
            hermes_profile=Path(
                env.get("FURBOMEK_HERMES_PROFILE", str(Path.home() / ".hermes/profiles/furbomek"))
            ),
            hermes_source=Path(
                env.get(
                    "FURBOMEK_HERMES_SOURCE",
                    str(Path.home() / ".local/share/hermes-agent-upstream"),
                )
            ),
            hermes_python=Path(
                env.get(
                    "FURBOMEK_HERMES_PYTHON",
                    str(Path.home() / ".hermes/tools/python-3.14.7+20260901-linux-x64/bin/python3"),
                )
            ),
            spool=spool,
        )

    @property
    def lock(self) -> Path:
        """Return the shared launcher lock path."""
        return self.media_root / "host-session.lock"

    @property
    def health(self) -> Path:
        """Return the atomic health document path."""
        return self.media_root / "health.json"


WorkerEnvironment: Final = "common", "bot-desktop"


@dataclass(frozen=True, slots=True)
class WorkerDefinition:
    """One child command and its lifecycle policy."""

    key: str
    argv: tuple[str, ...]
    log_name: str
    presentation: bool = False
    starts_after_configure: bool = False
    environment: Literal["common", "bot-desktop"] = "common"


@dataclass(frozen=True, slots=True)
class Freshness:
    """Validated artifact freshness at one health publication."""

    age_s: float | None
    fresh: bool
    schema_valid: bool


class FreshnessHealth(BaseModel):
    """Typed freshness summary for tracking and activity artifacts."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    tracking: Freshness
    activity: Freshness


class WorkerHealth(BaseModel):
    """Typed process status exposed for operational inspection."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    pid: int | None
    pgid: int | None
    status: WorkerStatus
    restarts_in_window: int
    last_exit: str | None


class HealthDocument(BaseModel):
    """Atomic, typed, non-claiming media-session health document."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    schema_version: Literal[1] = 1
    published_at_unix_ms: int = Field(ge=0)
    state: HealthState
    ready: bool
    record_requested: bool
    stop_reason: str | None = None
    freshness: FreshnessHealth
    workers: dict[str, WorkerHealth]
