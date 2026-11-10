from __future__ import annotations

import os
from dataclasses import replace
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest

from activity_models import ActivityEvent
from broker import ActivityBroker, RunConfig
from screen import CapturedFrame, DesktopHealth, ScreenPolicy, write_frame
from window_capture import NativeWindowCapture, WindowIdentity

NOW = 1_700_000_000_000


class FixedClock:
    def now_ms(self) -> int:
        return NOW

    def sleep(self, seconds: float) -> None:
        del seconds


def setup_broker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[ActivityBroker, WindowIdentity]:
    identity = WindowIdentity(42, 100, os.getuid(), 12.5, ":20", "desktop", 800, 600, "browser", "Browser")

    def health(_profile: Path) -> DesktopHealth:
        return DesktopHealth(True, {"DISPLAY": ":20"}, "desktop")

    def selected(_profile: Path, _window_id: int) -> WindowIdentity:
        return identity

    def capture(_self: NativeWindowCapture, _target: WindowIdentity) -> CapturedFrame:
        return CapturedFrame(b"jpeg", 800, 600, NOW)

    monkeypatch.setattr("runtime.desktop_health", health)
    monkeypatch.setattr("runtime.select_window", selected)
    monkeypatch.setattr(NativeWindowCapture, "capture", capture)
    broker = ActivityBroker(
        RunConfig(
            tmp_path / "absent-spool", tmp_path / "profile", tmp_path / "output", screen_policy=ScreenPolicy.APP_WINDOW
        ),
        FixedClock(),
    )
    return broker, identity


def screen(broker: ActivityBroker) -> str:
    return ActivityEvent.model_validate_json(
        (broker.config.out_dir / "activity.json").read_bytes()
    ).payload.screen.state


def test_selected_window_works_without_observer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    broker, identity = setup_broker(tmp_path, monkeypatch)
    assert broker.window_store is not None
    broker.window_store.share(identity)
    broker.step(NOW)
    assert screen(broker) == "live"
    broker.reader.close()


def test_recycled_pid_or_display_cannot_inherit_consent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    broker, identity = setup_broker(tmp_path, monkeypatch)
    assert broker.window_store is not None
    broker.window_store.share(replace(identity, process_start_time=1.0))
    broker.step(NOW)
    assert screen(broker) != "live"
    broker.reader.close()


def test_shutter_return_clears_public_metadata_and_frames(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    broker, identity = setup_broker(tmp_path, monkeypatch)
    assert broker.window_store is not None
    broker.window_store.share(identity)
    broker.step(NOW)
    broker.window_store.shutter()
    assert screen(broker) == "shuttered"
    assert not list(broker.config.out_dir.glob("hermes-screen-*.jpg"))
    broker.reader.close()


def test_broker_restart_rejects_previous_boot_consent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    broker, identity = setup_broker(tmp_path, monkeypatch)
    assert broker.window_store is not None
    old = broker.window_store.share(identity)
    other = ActivityBroker(broker.config)
    broker.window_store.path.write_text(old.model_dump_json(), encoding="utf-8")
    other.step(NOW)
    assert screen(other) != "live"
    broker.reader.close()
    other.reader.close()


def test_frame_files_are_private_even_with_permissive_caller_umask(tmp_path: Path) -> None:
    previous = os.umask(0)
    try:
        filename = write_frame(CapturedFrame(b"jpeg", 1, 1, NOW), tmp_path, 1)
    finally:
        os.umask(previous)
    assert (tmp_path / filename).stat().st_mode & 0o077 == 0


def test_shutter_serializes_with_inflight_publication(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    broker, identity = setup_broker(tmp_path, monkeypatch)
    assert broker.window_store is not None
    broker.window_store.share(identity)
    entered = Event()
    release = Event()

    def capture(_self: NativeWindowCapture, _target: WindowIdentity) -> CapturedFrame:
        entered.set()
        assert release.wait(timeout=2)
        return CapturedFrame(b"jpeg", 800, 600, NOW)

    monkeypatch.setattr(NativeWindowCapture, "capture", capture)
    with ThreadPoolExecutor(max_workers=2) as pool:
        frame = pool.submit(broker.step, NOW)
        assert entered.wait(timeout=2)
        shutter = pool.submit(broker.window_store.shutter)
        release.set()
        frame.result(timeout=3)
        shutter.result(timeout=3)
    assert screen(broker) == "shuttered"
    assert not list(broker.config.out_dir.glob("hermes-screen-*.jpg"))
    broker.reader.close()
