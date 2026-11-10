"""Typed X11 app-window enumeration and named-pixmap capture boundary."""

from __future__ import annotations

import os
import select
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from subprocess import PIPE, Popen
from typing import Final, Protocol

import psutil
from PIL import Image

from screen import SCREEN_SIZE, CapturedFrame, CaptureError, desktop_health, encode_jpeg, read_desktop_env

MAX_SOURCE_PIXELS: Final = 4096 * 4096
WINDOW_LINE_FIELDS: Final = 9
FRAME_HEADER_SIZE: Final = 28
HELPER_NAME: Final = "x11-window-capture"


@dataclass(frozen=True, slots=True)
class WindowIdentity:
    """Identity that must remain stable for an authorized capture."""

    window_id: int
    pid: int
    uid: int
    process_start_time: float
    display: str
    profile_generation: str
    width: int
    height: int
    instance: str
    class_name: str


@dataclass(frozen=True, slots=True)
class WindowInfo:
    """Operator-visible window listing entry with private identity metadata."""

    identity: WindowIdentity


class ReadableBinary(Protocol):
    """Small typed subprocess stream surface used by the frame decoder."""

    def fileno(self) -> int:
        """Return the underlying descriptor."""
        ...

    def read(self, size: int = -1, /) -> bytes:
        """Read bytes from the helper stream."""
        ...


def helper_path(profile_home: Path) -> Path:
    """Return the operator-installed private native helper."""
    path = profile_home / "app-window" / HELPER_NAME
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise CaptureError("app-window native helper is not installed") from exc
    if path.is_symlink() or not path.is_file() or metadata.st_uid != os.getuid() or not os.access(path, os.X_OK):
        raise CaptureError("app-window native helper is not a private executable")
    return path


def list_windows(profile_home: Path) -> tuple[WindowInfo, ...]:
    """List current-UID normal, viewable windows on the validated profile display."""
    health = desktop_health(profile_home)
    if not health.alive:
        raise CaptureError("dedicated app-window display is unavailable")
    helper = helper_path(profile_home)
    env = os.environ | dict(health.env)
    try:
        result = subprocess.run(
            (str(helper), "--list"),
            env=env,
            check=False,
            capture_output=True,
            text=True,
            timeout=2.0,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CaptureError("app-window enumeration failed") from exc
    if result.returncode != 0:
        raise CaptureError("app-window enumeration failed")
    generation = health.generation
    display = health.env.get("DISPLAY")
    if generation is None or display is None:
        raise CaptureError("dedicated app-window identity is incomplete")
    entries = tuple(_parse_window_line(line, generation, display) for line in result.stdout.splitlines() if line)
    return tuple(entry for entry in entries if _is_local(entry.identity))


def select_window(profile_home: Path, window_id: int) -> WindowIdentity:
    """Resolve one currently valid window identity by XID."""
    for entry in list_windows(profile_home):
        if entry.identity.window_id == window_id:
            return entry.identity
    raise CaptureError("selected window is no longer a valid local normal window")


class NativeWindowCapture:
    """Long-lived native helper connection for one validated display."""

    def __init__(self, profile_home: Path) -> None:
        """Open lazily so an off or shuttered broker never starts X capture."""
        self._profile_home: Path = profile_home
        self._process: Popen[bytes] | None = None

    def close(self) -> None:
        """Stop the helper process and release its X connection."""
        process = self._process
        self._process = None
        if process is None:
            return
        if process.stdin is not None:
            try:
                process.stdin.write(b"QUIT\n")
                process.stdin.flush()
            except BrokenPipeError:
                process.wait(timeout=2.0)
            finally:
                process.stdin.close()
        try:
            process.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        if process.stdout is not None:
            process.stdout.close()
        if process.stderr is not None:
            process.stderr.close()

    def capture(self, target: WindowIdentity) -> CapturedFrame:
        """Capture the selected named window pixmap and revalidate its identity."""
        process = self._ensure_process(target.display)
        stdin = process.stdin
        stdout = process.stdout
        if stdin is None or stdout is None:
            raise CaptureError("native app-window helper streams are unavailable")
        stdin.write(f"CAPTURE {target.window_id}\n".encode())
        stdin.flush()
        header = _read_exact(stdout, FRAME_HEADER_SIZE)
        if header[:4] == b"XERR":
            length = int.from_bytes(header[8:12], "big")
            message = _read_exact(stdout, length).decode("utf-8", errors="replace")
            raise CaptureError(message)
        if header[:4] != b"XCAP" or int.from_bytes(header[4:6], "big") != 1:
            raise CaptureError("native app-window frame header is invalid")
        width = int.from_bytes(header[8:12], "big")
        height = int.from_bytes(header[12:16], "big")
        payload_length = int.from_bytes(header[16:20], "big")
        if width < 1 or height < 1 or width * height > MAX_SOURCE_PIXELS or payload_length != width * height * 3:
            raise CaptureError("native app-window frame bounds are invalid")
        pixels = _read_exact(stdout, payload_length)
        current = select_window(self._profile_home, target.window_id)
        if current != target:
            raise CaptureError("selected window identity changed during capture")
        with Image.frombytes("RGB", (width, height), pixels) as image:
            image.thumbnail(SCREEN_SIZE)
            encoded = encode_jpeg(image)
            return CapturedFrame(encoded, image.width, image.height, _now_ms())

    def _ensure_process(self, display: str) -> Popen[bytes]:
        if self._process is not None:
            if self._process.poll() is not None:
                raise CaptureError("app-window connection ended; explicit resume is required")
            return self._process
        helper = helper_path(self._profile_home)
        environment = os.environ | dict(read_desktop_env(self._profile_home))
        environment["DISPLAY"] = display
        try:
            self._process = Popen((str(helper), "--serve"), env=environment, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        except OSError as exc:
            raise CaptureError("app-window native helper could not start") from exc
        return self._process


def _parse_window_line(line: str, generation: str, display: str) -> WindowInfo:
    fields = line.split("\t")
    if len(fields) != WINDOW_LINE_FIELDS:
        raise CaptureError("native app-window listing is malformed")
    window_id, pid, width, height = (int(value) for value in fields[:4])
    normal, viewable, override, instance, class_name = fields[4:]
    if normal != "1" or viewable != "1" or override != "0":
        raise CaptureError("native app-window listing contains an invalid target")
    process = psutil.Process(pid)
    return WindowInfo(
        WindowIdentity(
            window_id,
            pid,
            process.uids().real,
            process.create_time(),
            display,
            generation,
            width,
            height,
            instance,
            class_name,
        )
    )


def _is_local(identity: WindowIdentity) -> bool:
    return identity.uid == os.getuid()


def _read_exact(stream: ReadableBinary, size: int) -> bytes:
    chunks: list[bytes] = []
    remaining = size
    while remaining:
        readable, _, _ = select.select((stream.fileno(),), (), (), 2.0)
        if not readable:
            raise CaptureError("native app-window helper timed out")
        chunk = os.read(stream.fileno(), remaining)
        if not chunk:
            raise CaptureError("native app-window helper closed its frame stream")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _now_ms() -> int:
    return int(time.time() * 1000)
