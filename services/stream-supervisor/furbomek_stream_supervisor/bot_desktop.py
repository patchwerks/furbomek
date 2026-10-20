"""Future-qualified Hermes bot-desktop helper; not part of production activation."""

from __future__ import annotations

import contextlib
import os
import signal
import subprocess
from collections.abc import Mapping

from pydantic import ValidationError

from .models import BotDesktopRuntime, RuntimePaths
from .support import SessionError


def ensure_bot_desktop(
    paths: RuntimePaths, env: Mapping[str, str], timeout_s: float
) -> BotDesktopRuntime:
    """Start a fresh profile-scoped Hermes desktop through its installed API."""
    helper_env = dict(env)
    helper_env["HERMES_HOME"] = str(paths.hermes_profile)
    script = f"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, {str(paths.hermes_source)!r})
import hermes_bootstrap
from tools.bot_desktop import runtime

status = runtime.status()
if status.running:
    raise RuntimeError("profile-scoped bot desktop already running; refusing to reuse it")
runtime.start()
published = runtime.published_env()
base = runtime.state_dir().resolve()
env_path = base / "env"
pid_path = base / "launcher.pid"
if not env_path.is_file() or env_path.is_symlink() or env_path.stat().st_uid != os.getuid():
    raise RuntimeError("bot desktop env is not an owned regular file")
if not pid_path.is_file() or pid_path.is_symlink() or pid_path.stat().st_uid != os.getuid():
    raise RuntimeError("bot desktop launcher identity is not an owned regular file")
parts = pid_path.read_text(encoding="utf-8").split()
if len(parts) != 2:
    raise RuntimeError("bot desktop launcher identity is malformed")
pid = int(parts[0])
birth = float(parts[1])
os.kill(pid, 0)
auth = Path(published["XAUTHORITY"]).resolve()
if (
    auth.parent != base
    or not auth.is_file()
    or auth.is_symlink()
    or auth.stat().st_uid != os.getuid()
):
    raise RuntimeError("bot desktop XAUTHORITY is outside the owned profile state")
generation = f"{{pid}}:{{birth:.6f}}:{{auth.stat().st_ino}}"
print(json.dumps({{
    "display": published["DISPLAY"],
    "xauthority": str(auth),
    "pid": pid,
    "generation": generation,
}}))
"""
    try:
        child = subprocess.Popen(
            (str(paths.hermes_python), "-I", "-c", script),
            env=helper_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
        try:
            stdout, stderr = child.communicate(timeout=timeout_s)
        except subprocess.TimeoutExpired as error:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(child.pid, signal.SIGKILL)
            with contextlib.suppress(subprocess.TimeoutExpired):
                _ = child.communicate(timeout=1.0)
            msg = "bot desktop helper failed"
            raise SessionError(msg) from error
    except OSError as error:
        msg = "bot desktop helper failed"
        raise SessionError(msg) from error
    if child.returncode != 0:
        if "already running" in stderr:
            msg = "profile-scoped bot desktop already running; refusing to reuse it"
            raise SessionError(msg)
        msg = "bot desktop helper failed"
        raise SessionError(msg)
    try:
        return BotDesktopRuntime.model_validate_json(stdout)
    except ValidationError as error:
        msg = "bot desktop helper returned invalid runtime"
        raise SessionError(msg) from error
