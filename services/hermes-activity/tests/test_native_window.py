from __future__ import annotations

import os
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
import subprocess
import time
from typing import BinaryIO, TextIO

import pytest

ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / "native"
DISPLAY = os.environ.get("FURBOMEK_NATIVE_DISPLAY")
XAUTHORITY = os.environ.get("FURBOMEK_NATIVE_XAUTHORITY")
NATIVE_QA = DISPLAY is not None and XAUTHORITY is not None
pytestmark = pytest.mark.skipif(not NATIVE_QA, reason="set FURBOMEK_NATIVE_DISPLAY and FURBOMEK_NATIVE_XAUTHORITY")


@dataclass(frozen=True, slots=True)
class NativeBinaries:
    helper: Path
    canary: Path


@dataclass(frozen=True, slots=True)
class CanaryWindows:
    process: subprocess.Popen[str]
    target: int
    sibling: int


@dataclass(frozen=True, slots=True)
class NativeResponse:
    width: int
    height: int
    pixels: bytes
    error: str | None


@pytest.fixture(scope="module")
def native_binaries(tmp_path_factory: pytest.TempPathFactory) -> NativeBinaries:
    build_dir = tmp_path_factory.mktemp("native-window")
    helper = build_dir / "x11-window-capture"
    canary = build_dir / "x11-window-canary"
    environment = os.environ.copy()
    subprocess.run(
        ("bash", str(NATIVE / "build-x11-window-capture.sh"), str(helper)), check=True, cwd=ROOT, env=environment
    )
    subprocess.run(
        (
            "cc",
            "-std=c11",
            "-O2",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-D_POSIX_C_SOURCE=200809L",
            str(NATIVE / "x11-window-canary.c"),
            "-o",
            str(canary),
            "-lX11",
            "-l:libXcomposite.so.1",
        ),
        check=True,
        cwd=ROOT,
        env=environment,
    )
    return NativeBinaries(helper, canary)


@pytest.fixture
def canary(native_binaries: NativeBinaries) -> Iterator[CanaryWindows]:
    environment = _environment()
    process = subprocess.Popen(
        (str(native_binaries.canary),),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
        env=environment,
    )
    try:
        assert process.stdout is not None
        canary_output: TextIO = os.fdopen(os.dup(process.stdout.fileno()), "r", encoding="utf-8")
        ready = canary_output.readline().split()
        canary_output.close()
        assert ready[0] == "READY"
        windows = CanaryWindows(process, int(ready[1]), int(ready[2]))
        yield windows
    finally:
        if process.poll() is None and process.stdin is not None:
            process.stdin.write("QUIT\n")
            process.stdin.flush()
        process.wait(timeout=2)
        if process.stdin is not None:
            process.stdin.close()
        if process.stdout is not None:
            process.stdout.close()


def test_named_pixmap_has_rendered_pixels_and_excludes_occluding_sibling(
    native_binaries: NativeBinaries, canary: CanaryWindows, tmp_path: Path
) -> None:
    rows = _list_windows(native_binaries.helper)
    ids = {row[0] for row in rows}
    assert {canary.target, canary.sibling} <= ids

    response = _capture_once(native_binaries.helper, canary.target)
    assert response.error is None
    assert response.width == 240
    assert response.height == 160
    (tmp_path / "selected.rgb").write_bytes(response.pixels)
    colors = _color_counts(response.pixels)

    assert colors[(0, 255, 0)] == 16_000
    assert colors[(32, 32, 32)] == 22_400
    assert colors.get((0, 0, 255), 0) == 0


@pytest.mark.parametrize("lifecycle", ["UNMAP", "DESTROY"])
def test_serve_latches_unmap_and_destroy(
    native_binaries: NativeBinaries, canary: CanaryWindows, lifecycle: str
) -> None:
    environment = _environment()
    helper = subprocess.Popen(
        (str(native_binaries.helper), "--serve"), stdin=subprocess.PIPE, stdout=subprocess.PIPE, env=environment
    )
    assert helper.stdin is not None
    try:
        first = _capture_serve(helper, canary.target)
        assert first.error is None
        assert max(first.pixels) == 255
        assert canary.process.stdin is not None
        canary.process.stdin.write(f"{lifecycle}\n")
        canary.process.stdin.flush()
        time.sleep(0.05)
        ended = _capture_serve(helper, canary.target)
        assert ended.error is not None
        if lifecycle == "UNMAP":
            canary.process.stdin.write("REMAP\n")
            canary.process.stdin.flush()
            time.sleep(0.05)
            remapped = _capture_serve(helper, canary.target)
            assert remapped.error is not None
    finally:
        helper.stdin.write(b"QUIT\n")
        helper.stdin.flush()
        try:
            helper.wait(timeout=2)
        except subprocess.TimeoutExpired:
            helper.kill()
            helper.wait()
        if helper.stdin is not None:
            helper.stdin.close()
        if helper.stdout is not None:
            helper.stdout.close()


def test_list_rejects_foreign_client_machine(native_binaries: NativeBinaries, canary: CanaryWindows) -> None:
    assert canary.process.stdin is not None
    canary.process.stdin.write("FOREIGN\n")
    canary.process.stdin.flush()
    time.sleep(0.05)
    ids = {row[0] for row in _list_windows(native_binaries.helper)}
    assert canary.target not in ids
    assert canary.sibling in ids


def _environment() -> dict[str, str]:
    environment = os.environ.copy()
    assert DISPLAY is not None
    assert XAUTHORITY is not None
    environment["DISPLAY"] = DISPLAY
    environment["XAUTHORITY"] = XAUTHORITY
    return environment


def _list_windows(helper: Path) -> list[tuple[int, ...]]:
    result = subprocess.run((str(helper), "--list"), check=True, capture_output=True, text=True, env=_environment())
    rows: list[tuple[int, ...]] = []
    for line in result.stdout.splitlines():
        fields = line.split("\t")
        rows.append((int(fields[0]), int(fields[1]), int(fields[2]), int(fields[3])))
    return rows


def _capture_once(helper: Path, window_id: int) -> NativeResponse:
    result = subprocess.run(
        (str(helper), "--capture", str(window_id)), check=True, capture_output=True, env=_environment()
    )
    return _decode(result.stdout)


def _capture_serve(process: subprocess.Popen[bytes], window_id: int) -> NativeResponse:
    assert process.stdin is not None
    process.stdin.write(f"CAPTURE {window_id}\n".encode())
    process.stdin.flush()
    assert process.stdout is not None
    stream: BinaryIO = os.fdopen(os.dup(process.stdout.fileno()), "rb")
    try:
        header = _read_exact(stream, 28, process)
        length_offset = 8 if header[:4] == b"XERR" else 16
        length = int.from_bytes(header[length_offset : length_offset + 4], "big")
        return _decode(header + _read_exact(stream, length, process))
    finally:
        stream.close()


def _read_exact(stream: BinaryIO, size: int, process: subprocess.Popen[bytes]) -> bytes:
    chunks: list[bytes] = []
    remaining = size
    while remaining:
        chunk = stream.read(remaining)
        if not chunk:
            pytest.fail(f"native helper closed before {size} bytes; rc={process.poll()}")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _decode(raw: bytes) -> NativeResponse:
    assert len(raw) >= 28
    if raw[:4] == b"XERR":
        length = int.from_bytes(raw[8:12], "big")
        return NativeResponse(0, 0, b"", raw[28 : 28 + length].decode())
    assert raw[:4] == b"XCAP"
    width = int.from_bytes(raw[8:12], "big")
    height = int.from_bytes(raw[12:16], "big")
    length = int.from_bytes(raw[16:20], "big")
    return NativeResponse(width, height, raw[28 : 28 + length], None)


def _color_counts(pixels: bytes) -> dict[tuple[int, int, int], int]:
    counts: dict[tuple[int, int, int], int] = {}
    for offset in range(0, len(pixels), 3):
        color = (pixels[offset], pixels[offset + 1], pixels[offset + 2])
        counts[color] = counts.get(color, 0) + 1
    return counts
