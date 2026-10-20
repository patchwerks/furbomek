"""Typed command-line parsing and settings boundary."""

from __future__ import annotations

import argparse
import os
import stat
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from .models import RuntimePaths, RuntimeSettings, ScreenPolicy
from .runner import run_session
from .support import PRIVACY_BLOCKER, Dependencies, SessionError, SystemClock


class SettingsError(Exception):
    """Invalid or unsafe owner settings."""

    reason: str

    def __init__(self, reason: str) -> None:
        """Store the validation failure."""
        self.reason = reason
        super().__init__(reason)


@dataclass(frozen=True, slots=True)
class CliOptions:
    """Parsed supervisor command-line overrides."""

    record: bool
    settings: Path | None
    screen_policy: ScreenPolicy | None
    readiness_timeout_s: int | None


class CliNamespace(argparse.Namespace):
    """Typed namespace populated by argparse."""

    record: bool = False
    settings: Path | None = None
    screen_policy: str | None = None
    readiness_timeout_s: int | None = None


def parse_timeout(raw: str) -> int:
    """Parse the bounded readiness timeout used by argparse."""
    try:
        value = int(raw)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be an integer from 1 to 300") from error
    if not 1 <= value <= 300:
        raise argparse.ArgumentTypeError("must be an integer from 1 to 300")
    return value


def load_settings(path: Path | None) -> RuntimeSettings:
    """Load owner-only settings, treating a missing file as safe defaults."""
    if path is None:
        return RuntimeSettings()
    if path.is_symlink():
        raise SettingsError("settings path must be an owner-controlled regular file")
    if not path.exists():
        return RuntimeSettings()
    try:
        if not path.is_file():
            raise SettingsError("settings path must be an owner-controlled regular file")
        file_stat = path.stat()
        parent = path.parent.stat()
        if (
            not stat.S_ISREG(file_stat.st_mode)
            or file_stat.st_uid != os.getuid()
            or file_stat.st_mode & 0o077
            or parent.st_uid != os.getuid()
            or parent.st_mode & 0o077
        ):
            raise SettingsError("settings file must be owner-only")
        return RuntimeSettings.model_validate_json(path.read_bytes())
    except (OSError, ValidationError, ValueError) as error:
        raise SettingsError("invalid settings file") from error


def parse_cli(argv: Sequence[str] | None) -> CliOptions:
    """Parse bounded command-line overrides."""
    parser = argparse.ArgumentParser(description="Supervise the private Kinect2 media session.")
    _ = parser.add_argument("--record", action="store_true", help="request private OBS recording")
    _ = parser.add_argument("--settings", type=Path, help="owner-only runtime JSON settings")
    _ = parser.add_argument("--screen-policy", choices=[policy.value for policy in ScreenPolicy])
    _ = parser.add_argument("--readiness-timeout-s", type=parse_timeout)
    namespace = CliNamespace()
    _ = parser.parse_args(None if argv is None else list(argv), namespace=namespace)
    policy = ScreenPolicy(namespace.screen_policy) if namespace.screen_policy else None
    return CliOptions(namespace.record, namespace.settings, policy, namespace.readiness_timeout_s)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the supervisor CLI."""
    try:
        from .defaults import (
            REPO,
            build_worker_definitions,
            configure_obs,
            configure_obs_interruptible,
            graceful_obs_stop,
            runtime_environment,
        )

        options = parse_cli(argv)
        loaded = load_settings(options.settings)
        settings = RuntimeSettings(
            record=loaded.record or options.record,
            screen_policy=options.screen_policy or loaded.screen_policy,
            readiness_timeout_s=options.readiness_timeout_s or loaded.readiness_timeout_s,
        )
        if settings.screen_policy is ScreenPolicy.BOT_DESKTOP:
            raise SessionError(PRIVACY_BLOCKER)
        paths = RuntimePaths.from_environment(REPO, os.environ)
        env = runtime_environment(paths, os.environ)
        from .bot_desktop import ensure_bot_desktop

        deps = Dependencies(
            build_worker_definitions,
            configure_obs,
            ensure_bot_desktop,
            SystemClock(),
            graceful_obs_stop=graceful_obs_stop,
            configure_with_stop=configure_obs_interruptible,
        )
        return run_session(settings, paths, env, deps)
    except SystemExit as error:
        return int(error.code) if isinstance(error.code, int) else 1
    except (SettingsError, SessionError) as error:
        print(str(error), file=sys.stderr)
        return 2
    except OSError as error:
        print(f"session I/O failed: {error}", file=sys.stderr)
        return 1
