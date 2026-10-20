"""Shared lifecycle types and owner-lock helpers."""

from __future__ import annotations

import fcntl
import os
import time
from collections import deque
from collections.abc import Callable, Generator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from threading import Event
from types import FrameType
from typing import Protocol

import anyio

from .models import BotDesktopRuntime, RuntimePaths, RuntimeSettings, WorkerDefinition, WorkerStatus
from .processes import Clock, ManagedProcess, Sleep, spawn_process
from .readiness import ReadinessResult, check_readiness

MAX_RESTARTS = 5
RESTART_WINDOW_S = 300.0
BACKOFF_S = (1.0, 2.0, 4.0, 8.0, 16.0)
POLL_S = 0.05
PRIVACY_BLOCKER = (
    "live desktop screen publication is not qualified under observer-only privacy contract"
)


class SessionError(Exception):
    """Typed failure at the session boundary."""

    reason: str

    def __init__(self, reason: str) -> None:
        """Store the operator-facing failure reason."""
        self.reason = reason
        super().__init__(reason)


class RuntimeClock(Clock, Protocol):
    """Wall and monotonic clocks used by the runtime."""

    def time(self) -> float:
        """Return Unix seconds."""
        ...


class ConfigureRunner(Protocol):
    """Narrow seam for the OBS configuration executable."""

    def __call__(self, paths: RuntimePaths, env: Mapping[str, str], timeout_s: float) -> bool:
        """Run configuration and return whether it succeeded."""
        ...


class InterruptibleConfigureRunner(Protocol):
    """Owned configure process seam with cooperative stop observation."""

    def __call__(
        self, paths: RuntimePaths, env: Mapping[str, str], timeout_s: float, stop_event: Event
    ) -> bool:
        """Run configuration until success, failure, timeout, or stop request."""
        ...


class BotDesktopRunner(Protocol):
    """Narrow seam for the explicitly enabled Hermes desktop helper."""

    def __call__(
        self, paths: RuntimePaths, env: Mapping[str, str], timeout_s: float
    ) -> BotDesktopRuntime:
        """Ensure a fresh dedicated desktop and return its validated environment."""
        ...


class ObsGracefulStop(Protocol):
    """Narrow owned-OBS recording finalization seam."""

    def __call__(self, child: ManagedProcess, env: Mapping[str, str], timeout_s: float) -> bool:
        """Request OBS recording stop and return only after fresh stop evidence is observed."""
        ...


@dataclass(frozen=True, slots=True)
class Dependencies:
    """Injectable runtime seams kept narrower than the implementation."""

    workers: Callable[[RuntimeSettings, RuntimePaths], tuple[WorkerDefinition, ...]]
    configure: ConfigureRunner
    bot_desktop: BotDesktopRunner
    clock: RuntimeClock
    sleep: Sleep = anyio.sleep
    spawn: Callable[[WorkerDefinition, Mapping[str, str], Path], ManagedProcess] = spawn_process
    readiness: Callable[[Path, Callable[[], float], bool], ReadinessResult] = check_readiness
    graceful_obs_stop: ObsGracefulStop | None = None
    configure_with_stop: InterruptibleConfigureRunner | None = None


@dataclass(slots=True)
class WorkerState:
    """Mutable lifecycle record for one supervised worker."""

    definition: WorkerDefinition
    child: ManagedProcess | None = None
    status: WorkerStatus = WorkerStatus.NOT_STARTED
    restart_times: deque[float] = field(default_factory=deque)
    restart_at: float | None = None
    last_exit: str | None = None


class SystemClock:
    """Production clock implementation."""

    def monotonic(self) -> float:
        """Return monotonic seconds."""
        return time.monotonic()

    def time(self) -> float:
        """Return Unix seconds."""
        return time.time()


def ensure_directories(paths: RuntimePaths) -> None:
    """Create and verify owner-only session directories."""
    directories = (
        paths.media_root,
        paths.media_root / "logs",
        paths.media_root / "recordings",
        paths.media_root / "obs-config",
        paths.kinect_dir,
        paths.spool.parent,
    )
    for directory in directories:
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        _ = directory.chmod(0o700)
        if directory.stat().st_uid != os.getuid():
            msg = f"session directory is not owner-controlled: {directory}"
            raise SessionError(msg)


@contextmanager
def session_lock(path: Path) -> Generator[None, None, None]:
    """Hold the same non-blocking lock as the working launcher."""
    handle = path.open("a+b")
    _ = path.chmod(0o600)
    try:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            msg = "The host Kinect session is already running."
            raise SessionError(msg) from error
        yield
    finally:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


SignalHandler = Callable[[int, FrameType | None], None] | int | None
