"""Dedicated desktop health and bounded in-memory JPEG capture."""

from __future__ import annotations

import hashlib
import math
import os
import re
import time
from dataclasses import dataclass
from enum import StrEnum
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, Final, Literal, cast, override

import psutil

if TYPE_CHECKING:
    from collections.abc import Mapping

from PIL import Image, ImageGrab

from activity_models import ScreenState

SCREEN_RING: Final = 2
SCREEN_SIZE: Final = (1_280, 800)
SCREEN_MAX_AGE_MS: Final = 2_000
SCREEN_MAX_BYTES: Final = 2 * 1024 * 1024
_DEDICATED_DISPLAY: Final = re.compile(r"^:(?:2[0-9]|[3-8][0-9])(?:\.0)?$")


class ScreenPolicy(StrEnum):
    """Explicit capture policy."""

    OFF = "off"
    BOT_DESKTOP = "bot-desktop"


@dataclass(frozen=True, slots=True)
class DesktopHealth:
    """Validated dedicated desktop identity."""

    alive: bool
    env: Mapping[str, str]
    generation: str | None


@dataclass(frozen=True, slots=True)
class CapturedFrame:
    """In-memory bounded capture candidate."""

    data: bytes
    width: int
    height: int
    captured_at_ms: int


@dataclass(frozen=True, slots=True)
class CaptureError(RuntimeError):
    """Capture failed before publication."""

    reason: str

    @override
    def __str__(self) -> str:
        return self.reason


def read_desktop_env(profile_home: Path) -> Mapping[str, str]:
    """Read only the dedicated bot-desktop display variables."""
    bot_dir = profile_home / "bot-desktop"
    _require_owner_directory(bot_dir)
    env_path = bot_dir / "env"
    _require_owner_file(env_path)
    values: dict[str, str] = {}
    raw = env_path.read_text(encoding="utf-8")
    for line in raw.splitlines():
        key, separator, value = line.partition("=")
        if separator and key in ("DISPLAY", "XAUTHORITY"):
            values[key] = value.strip()
    return values


def desktop_health(profile_home: Path) -> DesktopHealth:
    """Validate the explicit dedicated desktop profile and process."""
    bot_dir = profile_home / "bot-desktop"
    pid_path = bot_dir / "launcher.pid"
    try:
        env = read_desktop_env(profile_home)
        _require_owner_file(pid_path)
        pid_parts = pid_path.read_text(encoding="utf-8").split()
        pid = int(pid_parts[0])
        expected_create_time = float(pid_parts[1]) if len(pid_parts) > 1 else None
        expected_identity = pid_parts[2] if len(pid_parts) > 2 else None
        raw_auth_path = Path(env["XAUTHORITY"])
        _require_owner_file(raw_auth_path)
        auth_path = raw_auth_path.resolve(strict=True)
        auth_path.relative_to(bot_dir.resolve(strict=True))
        _require_owner_file(auth_path)
    except (KeyError, OSError, ValueError, IndexError):
        return DesktopHealth(False, {}, None)
    display = env.get("DISPLAY", "")
    if not _DEDICATED_DISPLAY.fullmatch(display) or pid <= 0:
        return DesktopHealth(False, env, None)
    try:
        os.kill(pid, 0)
        create_time, identity = _launcher_identity(pid)
    except (OSError, ValueError, psutil.Error):
        return DesktopHealth(False, env, None)
    if expected_create_time is not None and abs(expected_create_time - create_time) > 1.0:
        return DesktopHealth(False, env, None)
    if expected_identity is not None and expected_identity not in identity:
        return DesktopHealth(False, env, None)
    generation = f"{pid}:{create_time:.3f}:{hashlib.sha256(identity.encode()).hexdigest()}:{display}"
    return DesktopHealth(True, env, generation)


def _require_owner_directory(path: Path) -> None:
    metadata = path.lstat()
    if path.is_symlink() or not path.is_dir() or metadata.st_uid != os.getuid() or metadata.st_mode & 0o077:
        raise OSError("bot desktop directory is not owner-only")


def _require_owner_file(path: Path) -> None:
    metadata = path.lstat()
    if path.is_symlink() or not path.is_file() or metadata.st_uid != os.getuid() or metadata.st_mode & 0o077:
        raise OSError("bot desktop file is not owner-only")


def _launcher_identity(pid: int) -> tuple[float, str]:
    process = psutil.Process(pid)
    # Native psutil metadata is untyped on some platforms; validate that boundary.
    raw_create_time = cast("object", process.create_time())
    raw_cmdline = cast("object", process.cmdline())
    try:
        return _validated_launcher_metadata(raw_create_time, raw_cmdline)
    except (TypeError, OverflowError) as exc:
        raise ValueError("launcher metadata has an invalid type or range") from exc


def _validated_launcher_metadata(raw_create_time: object, raw_cmdline: object) -> tuple[float, str]:
    if isinstance(raw_create_time, bool) or not isinstance(raw_create_time, (int, float)):
        raise TypeError("launcher creation time is not numeric")
    create_time = float(raw_create_time)
    if not math.isfinite(create_time) or create_time <= 0:
        raise ValueError("launcher creation time is not finite and positive")
    if not isinstance(raw_cmdline, list):
        raise TypeError("launcher command line is not a list")
    arguments: list[str] = []
    for argument in cast("list[object]", raw_cmdline):
        if not isinstance(argument, str):
            raise TypeError("launcher command line contains a non-string argument")
        arguments.append(argument)
    identity = " ".join(arguments)
    if not identity or not any(token in identity.lower() for token in ("launcher", "bot-desktop")):
        raise ValueError("process is not the dedicated bot desktop launcher")
    return create_time, identity


def capture_frame(env: Mapping[str, str]) -> CapturedFrame:
    """Capture and encode a bounded candidate without publishing it."""
    display = env.get("DISPLAY", "")
    authority = env.get("XAUTHORITY", "")
    if not _DEDICATED_DISPLAY.fullmatch(display) or not authority:
        raise CaptureError("dedicated desktop environment is invalid")
    previous = os.environ.get("XAUTHORITY")
    os.environ["XAUTHORITY"] = authority
    try:
        try:
            image = ImageGrab.grab(xdisplay=display)
        except (OSError, ValueError) as exc:
            raise CaptureError("dedicated desktop capture failed") from exc
    finally:
        if previous is None:
            os.environ.pop("XAUTHORITY", None)
        else:
            os.environ["XAUTHORITY"] = previous
    image = image.convert("RGB")
    image.thumbnail(SCREEN_SIZE)
    data = _encode_jpeg(image)
    return CapturedFrame(data, image.width, image.height, _now_ms())


def write_frame(frame: CapturedFrame, out_dir: Path, slot: int) -> str:
    """Atomically publish one already-approved frame into the fixed ring."""
    filename = f"hermes-screen-{slot % SCREEN_RING}.jpg"
    pending = out_dir / f".{filename}.pending"
    pending.write_bytes(frame.data)
    pending.replace(out_dir / filename)
    return filename


def invalidate_frames(out_dir: Path) -> None:
    """Remove all old pixels when the screen is not publishable."""
    for slot in range(SCREEN_RING):
        (out_dir / f"hermes-screen-{slot}.jpg").unlink(missing_ok=True)


def offline_screen(seq: int, slot: int, state: Literal["offline", "shuttered"] = "offline") -> ScreenState:
    """Build a non-live screen state that cannot reference old dimensions."""
    return ScreenState(
        state=state,
        filename=f"hermes-screen-{slot % SCREEN_RING}.jpg",
        seq=seq,
        width=1_280,
        height=800,
        captured_at_ms=0,
    )


def live_screen(frame: CapturedFrame, seq: int, filename: str) -> ScreenState:
    """Build live metadata from the actual captured image."""
    return ScreenState(
        state="live",
        filename=filename,
        seq=seq,
        width=frame.width,
        height=frame.height,
        captured_at_ms=frame.captured_at_ms,
    )


def _encode_jpeg(image: Image.Image) -> bytes:
    for quality in (82, 70, 55, 40):
        output = BytesIO()
        image.save(output, format="JPEG", quality=quality, optimize=True)
        data = output.getvalue()
        if len(data) <= SCREEN_MAX_BYTES:
            return data
    raise CaptureError("captured desktop frame exceeds size limit")


def _now_ms() -> int:
    return int(time.time() * 1000)
