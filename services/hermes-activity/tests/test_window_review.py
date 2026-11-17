from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import NoReturn

import psutil
import pytest

from screen import CaptureError, DesktopHealth
from window_capture import helper_path, list_windows
from window_consent import WindowConsentStore
from broker import ActivityBroker, RunConfig
from screen import ScreenPolicy


@pytest.mark.parametrize("policy", ["off", "app-window", "bot-desktop", "unknown"])
def test_untyped_policy_cannot_activate_broker(tmp_path: Path, policy: str) -> None:
    output = tmp_path / "output"
    program = (
        "from pathlib import Path; from broker import ActivityBroker, RunConfig; "
        f"ActivityBroker(RunConfig(Path('unused'), Path('unused'), Path({str(output)!r}), screen_policy={policy!r}))"
    )
    result = subprocess.run([sys.executable, "-c", program], check=False, capture_output=True)
    assert result.returncode != 0
    assert not output.exists()


@pytest.mark.parametrize(("mode", "parent"), [(0o777, False), (0o722, False), (0o777, True)])
def test_helper_admission_rejects_unsafe_permissions(tmp_path: Path, mode: int, *, parent: bool) -> None:
    directory = tmp_path / "app-window"
    directory.mkdir(mode=0o700)
    helper = directory / "x11-window-capture"
    helper.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    helper.chmod(0o700)
    (directory if parent else helper).chmod(mode)
    with pytest.raises(CaptureError):
        helper_path(tmp_path)


def test_enumeration_skips_disappearing_process(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    directory = tmp_path / "app-window"
    directory.mkdir(mode=0o700)
    helper = directory / "x11-window-capture"
    helper.write_text("#!/bin/sh\nprintf '42\\t999\\t1\\t1\\t1\\t1\\t0\\tapp\\tApp\\n'\n", encoding="utf-8")
    helper.chmod(0o700)

    def health(_profile: Path) -> DesktopHealth:
        return DesktopHealth(True, {"DISPLAY": ":28", "XAUTHORITY": "unused"}, "server")

    def vanished(_pid: int) -> NoReturn:
        raise psutil.NoSuchProcess(999)

    monkeypatch.setattr("window_capture.desktop_health", health)
    monkeypatch.setattr("window_capture.psutil.Process", vanished)
    assert list_windows(tmp_path) == ()


def test_native_helper_receives_no_inherited_secrets(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    directory = tmp_path / "app-window"
    directory.mkdir(mode=0o700)
    helper = directory / "x11-window-capture"
    helper.write_text('#!/bin/sh\ntest -z "$PRIVATE_TEST_TOKEN"\n', encoding="utf-8")
    helper.chmod(0o700)

    def health(_profile: Path) -> DesktopHealth:
        return DesktopHealth(True, {"DISPLAY": ":28", "XAUTHORITY": "unused"}, "server")

    monkeypatch.setattr("window_capture.desktop_health", health)
    monkeypatch.setenv("PRIVATE_TEST_TOKEN", "canary-not-a-credential")
    assert list_windows(tmp_path) == ()
    assert os.getuid() == helper.stat().st_uid


def test_typed_desktop_policy_is_rejected_before_output(tmp_path: Path) -> None:
    output = tmp_path / "output"
    with pytest.raises(ValueError, match="capture"):
        ActivityBroker(
            RunConfig(tmp_path / "spool", tmp_path / "profile", output, screen_policy=ScreenPolicy.BOT_DESKTOP)
        )
    assert not output.exists()


def test_capture_error_survives_context_manager_traceback(tmp_path: Path) -> None:
    store = WindowConsentStore(tmp_path / "profile", tmp_path / "output")
    message = "capture failed"
    with pytest.raises(CaptureError), store.locked():
        raise CaptureError(message)


def test_helper_rejects_replaceable_profile_directory(tmp_path: Path) -> None:
    directory = tmp_path / "app-window"
    directory.mkdir(mode=0o700)
    helper = directory / "x11-window-capture"
    helper.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    helper.chmod(0o700)
    tmp_path.chmod(0o777)
    with pytest.raises(CaptureError):
        helper_path(tmp_path)
