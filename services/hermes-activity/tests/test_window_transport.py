from __future__ import annotations

import os
import sys
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image
import psutil

import pytest

from screen import CaptureError
from window_capture import NativeWindowCapture, WindowIdentity

if TYPE_CHECKING:
    from collections.abc import Mapping


def make_capture(
    tmp_path: Path, body: str, monkeypatch: pytest.MonkeyPatch
) -> tuple[NativeWindowCapture, WindowIdentity]:
    directory = tmp_path / "app-window"
    directory.mkdir(mode=0o700)
    helper = directory / "x11-window-capture"
    program = f"#!{sys.executable}\nimport os\nfrom pathlib import Path\n"
    program += f"Path({str(tmp_path / 'helper.pid')!r}).write_text(str(os.getpid()))\n{body}"
    helper.write_text(program, encoding="utf-8")
    helper.chmod(0o700)
    identity = WindowIdentity(42, 100, os.getuid(), 12.5, ":28", "server", 1, 1, "test", "Test")

    def environment(_profile: Path) -> Mapping[str, str]:
        return {"DISPLAY": ":28", "XAUTHORITY": "unused"}

    def selected(_profile: Path, _window: int) -> WindowIdentity:
        return identity

    monkeypatch.setattr("window_capture.read_desktop_env", environment)
    monkeypatch.setattr("window_capture.select_window", selected)
    return NativeWindowCapture(tmp_path), identity


def test_production_decoder_handles_fragmented_real_pipe(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    capture, identity = make_capture(
        tmp_path,
        """
import os, struct, sys
assert 'PRIVATE_TEST_TOKEN' not in os.environ
for request in sys.stdin:
    if request.startswith('QUIT'):
        break
    sys.stdout.buffer.write(struct.pack('>4sHHIIIQ', b'XCAP', 1, 0, 1, 1, 3, 1) + bytes((255, 0, 0)))
    sys.stdout.buffer.flush()
""",
        monkeypatch,
    )
    read = os.read

    def fragmented(descriptor: int, size: int) -> bytes:
        return read(descriptor, min(size, 2))

    monkeypatch.setattr("window_capture.os.read", fragmented)
    monkeypatch.setenv("PRIVATE_TEST_TOKEN", "canary-not-a-credential")
    try:
        frame = capture.capture(identity)
        assert (frame.width, frame.height) == (1, 1)
        with Image.open(BytesIO(frame.data)) as image:
            assert image.convert("RGB").tobytes()[0] > 200
    finally:
        capture.close()


@pytest.mark.parametrize("body", ["raise SystemExit(1)\n", "import signal,sys\nsys.stdin.readline()\nsignal.pause()\n"])
def test_failure_reaps_helper_and_closes_all_pipes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, body: str) -> None:
    capture, identity = make_capture(tmp_path, body, monkeypatch)
    descriptors = psutil.Process().num_fds()
    with pytest.raises(CaptureError):
        capture.capture(identity)
    pid = int((tmp_path / "helper.pid").read_text(encoding="utf-8"))
    assert not psutil.pid_exists(pid)
    assert psutil.Process().num_fds() == descriptors
