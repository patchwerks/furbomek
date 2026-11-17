"""Public runtime configuration and broker entry point."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final, Protocol

from screen import (
    ScreenPolicy,
    capture_frame,
    desktop_health,
    invalidate_frames,
    live_screen,
    offline_screen,
    write_frame,
)
from window_capture import NativeWindowCapture, select_window

if TYPE_CHECKING:
    from activity_broker import ActivityBroker

HEARTBEAT_MS: Final = 1_000
ACTIVE_FRAME_MS: Final = 250
IDLE_FRAME_MS: Final = 1_000


class Clock(Protocol):
    """Clock seam used by deterministic broker tests."""

    def now_ms(self) -> int:
        """Return current Unix milliseconds."""
        ...

    def sleep(self, seconds: float) -> None:
        """Sleep between polling cycles."""
        ...


class SystemClock:
    """Wall-clock implementation used by the CLI."""

    def now_ms(self) -> int:
        """Return current Unix milliseconds."""
        return int(time.time() * 1000)

    def sleep(self, seconds: float) -> None:
        """Sleep between polling cycles."""
        time.sleep(seconds)


@dataclass(frozen=True, slots=True)
class RunConfig:
    """Paths and policy for one broker process."""

    spool: Path
    profile_home: Path
    out_dir: Path
    once: bool = False
    screen_policy: ScreenPolicy = ScreenPolicy.OFF
    character_session: str | None = None
    window_id: int | None = None


def run(config: RunConfig, clock: Clock | None = None) -> None:
    """Run one configured activity broker."""
    from activity_broker import ActivityBroker  # noqa: PLC0415

    ActivityBroker(config, clock).run()


__all__ = [
    "IDLE_FRAME_MS",
    "ActivityBroker",
    "Clock",
    "NativeWindowCapture",
    "RunConfig",
    "SystemClock",
    "capture_frame",
    "desktop_health",
    "invalidate_frames",
    "live_screen",
    "offline_screen",
    "os",
    "run",
    "select_window",
    "write_frame",
]


def __getattr__(name: str) -> type[ActivityBroker]:
    """Load the broker class lazily to preserve the legacy runtime seam."""
    if name != "ActivityBroker":
        raise AttributeError(name)
    from activity_broker import ActivityBroker as BrokerClass  # noqa: PLC0415

    return BrokerClass
