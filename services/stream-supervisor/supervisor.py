#!/usr/bin/env python3
"""Foreground executable facade for the private media-session supervisor."""

from __future__ import annotations

from collections.abc import Sequence

from furbomek_stream_supervisor.bot_desktop import ensure_bot_desktop
from furbomek_stream_supervisor.cli import load_settings
from furbomek_stream_supervisor.cli import main as _cli_main
from furbomek_stream_supervisor.defaults import (
    REPO,
    build_worker_definitions,
    configure_obs,
    configure_obs_interruptible,
    graceful_obs_stop,
    runtime_environment,
)

__all__ = [
    "REPO",
    "build_worker_definitions",
    "configure_obs",
    "configure_obs_interruptible",
    "ensure_bot_desktop",
    "graceful_obs_stop",
    "load_settings",
    "main",
    "runtime_environment",
]


def main(argv: Sequence[str] | None = None) -> int:
    """Run the supervisor CLI."""
    return _cli_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
