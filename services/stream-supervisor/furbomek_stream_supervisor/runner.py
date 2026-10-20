"""Foreground signal and lock adapter for one session."""

from __future__ import annotations

import signal
from collections.abc import Mapping
from types import FrameType

import anyio

from .models import RuntimePaths, RuntimeSettings, ScreenPolicy
from .ownership import OwnershipError, assert_available, record_owners
from .session import Session
from .support import (
    PRIVACY_BLOCKER,
    Dependencies,
    SessionError,
    SignalHandler,
    ensure_directories,
    session_lock,
)


def install_signal_handlers(session: Session) -> dict[signal.Signals, SignalHandler]:
    """Install prompt signal handlers and return the previous handlers."""
    previous: dict[signal.Signals, SignalHandler] = {}

    def stop(_signum: int, _frame: FrameType | None) -> None:
        session.request_stop("interrupted", success=True)

    for value in (signal.SIGINT, signal.SIGTERM):
        previous[value] = signal.getsignal(value)
        _ = signal.signal(value, stop)
    return previous


def restore_signal_handlers(previous: Mapping[signal.Signals, SignalHandler]) -> None:
    """Restore handlers after one foreground session."""
    for value, handler in previous.items():
        _ = signal.signal(value, handler)


def run_session(
    settings: RuntimeSettings,
    paths: RuntimePaths,
    env: Mapping[str, str],
    deps: Dependencies,
) -> int:
    """Run a session while holding the duplicate-owner lock."""
    if settings.screen_policy is ScreenPolicy.BOT_DESKTOP:
        raise SessionError(PRIVACY_BLOCKER)
    ensure_directories(paths)
    with session_lock(paths.lock):
        try:
            assert_available(paths.owners)
        except OwnershipError as error:
            raise SessionError(str(error)) from error
        record_owners(paths.owners, {})
        session = Session(settings, paths, env, deps)
        previous = install_signal_handlers(session)
        try:
            return anyio.run(session.run)
        finally:
            restore_signal_handlers(previous)
