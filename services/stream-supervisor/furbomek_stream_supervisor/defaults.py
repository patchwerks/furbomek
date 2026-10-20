"""Production worker commands and external executable adapters."""

from __future__ import annotations

import contextlib
import os
import signal
import subprocess
import time
from collections.abc import Mapping
from pathlib import Path
from threading import Event

from furbomek_stream_supervisor.models import (
    RuntimePaths,
    RuntimeSettings,
    WorkerDefinition,
)
from furbomek_stream_supervisor.processes import ManagedProcess

REPO = Path(__file__).resolve().parents[3]


def runtime_environment(paths: RuntimePaths, source: Mapping[str, str]) -> Mapping[str, str]:
    """Build child environment from the actual caller display variables."""
    env = dict(source)
    env.update(
        {
            "FURBOMEK_MEDIA_ROOT": str(paths.media_root),
            "FURBOMEK_KINECT_DIR": str(paths.kinect_dir),
            "FURBOMEK_ACTIVITY_SPOOL": str(paths.spool),
            "FURBOMEK_HERMES_PROFILE": str(paths.hermes_profile),
            "XDG_CONFIG_HOME": str(paths.media_root / "obs-config"),
            "QT_QPA_PLATFORM": "xcb",
        }
    )
    return env


def build_worker_definitions(
    settings: RuntimeSettings, paths: RuntimePaths
) -> tuple[WorkerDefinition, ...]:
    """Build the exact private capture, activity, viewer, and OBS commands."""
    capture = (str(paths.media_root / "capture-build/furbomek-kinect2"),)
    tracker = (
        "uv",
        "run",
        "--no-project",
        "--python",
        "/usr/bin/python3.12",
        str(paths.repo / "services/camera-capture/track.py"),
    )
    broker = (
        "uv",
        "run",
        "--project",
        str(paths.repo / "services/hermes-activity"),
        "--frozen",
        "python",
        str(paths.repo / "services/hermes-activity/broker.py"),
        str(paths.spool),
        str(paths.hermes_profile),
        str(paths.kinect_dir),
        "--screen-policy",
        settings.screen_policy.value,
    )
    viewer = (
        str(paths.media_root / "godot/godot"),
        "--path",
        str(paths.repo / "tools/kinect2/godot"),
    )
    obs_args = [
        "obs",
        "--multi",
        "--profile",
        "Kinect2",
        "--collection",
        "Kinect2",
        "--disable-missing-files-check",
    ]
    if settings.record:
        obs_args.append("--startrecording")
    return (
        WorkerDefinition("capture", capture, "capture.log"),
        WorkerDefinition("tracker", tracker, "tracking.log"),
        WorkerDefinition("broker", broker, "broker.log", environment="bot-desktop"),
        WorkerDefinition("viewer", viewer, "godot.log", presentation=True),
        WorkerDefinition(
            "obs", tuple(obs_args), "obs-launch.log", presentation=True, starts_after_configure=True
        ),
    )


def _configure_obs(
    paths: RuntimePaths, env: Mapping[str, str], timeout_s: float, stop_event: Event | None
) -> bool:
    log_path = paths.media_root / "logs/obs-configure.log"
    log_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with log_path.open("ab") as log:
        try:
            child = subprocess.Popen(
                ("node", str(paths.repo / "tools/kinect2/configure-obs.mjs")),
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                env=dict(env),
                start_new_session=True,
            )
        except OSError:
            return False
        deadline = time.monotonic() + timeout_s
        while child.poll() is None and time.monotonic() < deadline:
            if stop_event is not None and stop_event.is_set():
                break
            time.sleep(0.05)
        if child.poll() is not None:
            return child.returncode == 0
        with contextlib.suppress(ProcessLookupError):
            os.killpg(child.pid, signal.SIGTERM)
        term_deadline = time.monotonic() + min(0.5, max(0.05, timeout_s))
        while child.poll() is None and time.monotonic() < term_deadline:
            time.sleep(0.02)
        if child.poll() is None:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(child.pid, signal.SIGKILL)
        with contextlib.suppress(subprocess.TimeoutExpired):
            _ = child.wait(timeout=0.5)
        return False


def configure_obs(paths: RuntimePaths, env: Mapping[str, str], timeout_s: float) -> bool:
    """Run the existing OBS configurator in its own process group."""
    return _configure_obs(paths, env, timeout_s, None)


def configure_obs_interruptible(
    paths: RuntimePaths, env: Mapping[str, str], timeout_s: float, stop_event: Event
) -> bool:
    """Run OBS configuration while allowing the session signal handler to stop it."""
    return _configure_obs(paths, env, timeout_s, stop_event)


def graceful_obs_stop(child: ManagedProcess, env: Mapping[str, str], timeout_s: float) -> bool:
    """Stop recording through a verified owned OBS window and await a fresh log marker."""
    result = child.poll() is not None
    if result or not env.get("DISPLAY"):
        return result
    command_env = dict(env)
    try:
        marker_start = child.log_path.stat().st_size
        windows = subprocess.run(
            (
                "xdotool",
                "search",
                "--onlyvisible",
                "--all",
                "--pid",
                str(child.pid),
                "--class",
                "obs",
            ),
            env=command_env,
            capture_output=True,
            text=True,
            timeout=1.0,
            check=False,
        ).stdout.splitlines()
        owned_window = next((window for window in windows if window.strip()), None)
        if owned_window is not None:
            _ = subprocess.run(
                ("xdotool", "windowactivate", "--sync", owned_window),
                env=command_env,
                capture_output=True,
                text=True,
                timeout=1.0,
                check=True,
            )
            _ = subprocess.run(
                ("xdotool", "key", "--window", owned_window, "F10"),
                env=command_env,
                capture_output=True,
                text=True,
                timeout=1.0,
                check=True,
            )
            deadline = time.monotonic() + timeout_s
            while time.monotonic() < deadline:
                fresh_log = child.log_path.read_bytes()[marker_start:].lower()
                if any(
                    marker in fresh_log
                    for marker in (b"recording stopped", b"output stopped", b"': stopping")
                ):
                    result = True
                    break
                time.sleep(0.05)
    except (OSError, subprocess.SubprocessError):
        result = False
    return result
