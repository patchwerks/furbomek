"""Executable Hermes activity broker facade."""

from __future__ import annotations

import runpy

from activity_models import BrokerState
from reducer import apply_event, idle_state, refresh_timeline
from runtime import ActivityBroker, RunConfig, run
from screen import ScreenPolicy, capture_frame

__all__ = [
    "ActivityBroker",
    "BrokerState",
    "RunConfig",
    "ScreenPolicy",
    "apply_event",
    "capture_frame",
    "idle_state",
    "refresh_timeline",
    "run",
]


def main() -> None:
    """Invoke the locked broker CLI."""
    _ = runpy.run_module("cli", run_name="__main__")


if __name__ == "__main__":
    main()
