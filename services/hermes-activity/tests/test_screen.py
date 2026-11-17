from __future__ import annotations

import os
from pathlib import Path
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from activity_models import ActivityEvent
from broker import ActivityBroker, RunConfig
from hermes_feed import SpoolEvent
from screen import CapturedFrame, DesktopHealth, ScreenPolicy, desktop_health
from window_capture import NativeWindowCapture, WindowIdentity

NOW = 1_700_000_000_000


class FixedClock:
    def now_ms(self) -> int:
        return NOW

    def sleep(self, seconds: float) -> None:
        del seconds


def health(_profile_home: Path) -> DesktopHealth:
    return DesktopHealth(True, {"DISPLAY": ":28", "XAUTHORITY": "/tmp/bot.xauth"}, "generation-1")


def target(_profile: Path, _window_id: int) -> WindowIdentity:
    return WindowIdentity(42, 100, os.getuid(), 12.5, ":28", "generation-1", 1, 1, "app", "App")


def navigation_events() -> str:
    pre = SpoolEvent(
        kind="tool",
        ts_ms=NOW,
        session="s",
        phase="running",
        category="BROWSER",
        action="opening",
        detail="example.com",
        call="navigation",
    )
    post = pre.model_copy(update={"phase": "ok", "privacy_release": True})
    return pre.model_dump_json() + "\n" + post.model_dump_json() + "\n"


def test_false_dedicated_display_health_is_offline(tmp_path: Path) -> None:
    desktop = tmp_path / "bot-desktop"
    desktop.mkdir()
    authority = tmp_path / "xauth"
    authority.write_bytes(b"x")
    authority.chmod(0o600)
    (desktop / "env").write_text(f"DISPLAY=:0\nXAUTHORITY={authority}\n", encoding="utf-8")
    (desktop / "launcher.pid").write_text(str(os.getpid()), encoding="utf-8")
    result = desktop_health(tmp_path)
    assert not result.alive
    assert result.generation is None


def test_safe_release_publishes_only_a_fresh_frame(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    spool = tmp_path / "events.jsonl"
    spool.write_text(navigation_events(), encoding="utf-8")
    output = tmp_path / "output"
    monkeypatch.setattr("runtime.desktop_health", health)

    def fake_capture(_self: NativeWindowCapture, _target: WindowIdentity) -> CapturedFrame:
        return CapturedFrame(b"jpeg", 1, 1, NOW)

    monkeypatch.setattr("runtime.NativeWindowCapture.capture", fake_capture)
    monkeypatch.setattr("runtime.select_window", target)

    broker = ActivityBroker(RunConfig(spool, tmp_path, output, screen_policy=ScreenPolicy.APP_WINDOW), FixedClock())
    assert broker.window_store is not None
    broker.window_store.share(target(tmp_path, 42))
    broker.step(NOW)
    event = ActivityEvent.model_validate_json((output / "activity.json").read_text(encoding="utf-8"))
    assert event.payload.screen.state == "live"
    assert event.payload.screen.filename in {"hermes-screen-0.jpg", "hermes-screen-1.jpg"}
    assert event.payload.screen.width <= 1_280
    assert event.payload.screen.height <= 800
    assert event.payload.screen.ttl_ms == 2_000
    assert (output / "hermes-screen-1.jpg").is_file()
    broker.reader.close()


def test_privacy_release_never_authorizes_unconsented_pixels(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    spool = tmp_path / "events.jsonl"
    spool.write_text(navigation_events(), encoding="utf-8")
    output = tmp_path / "output"

    def forbidden_capture(_self: NativeWindowCapture, _target: WindowIdentity) -> CapturedFrame:
        message = "observer release cannot authorize window capture"
        raise AssertionError(message)

    monkeypatch.setattr("runtime.desktop_health", health)
    monkeypatch.setattr("runtime.NativeWindowCapture.capture", forbidden_capture)

    ActivityBroker(
        RunConfig(spool, tmp_path, output, once=True, screen_policy=ScreenPolicy.APP_WINDOW), FixedClock()
    ).run()
    event = ActivityEvent.model_validate_json((output / "activity.json").read_text(encoding="utf-8"))
    assert event.payload.screen.state == "shuttered"
    assert not (output / "hermes-screen-1.jpg").exists()


def test_new_frame_is_published_before_heartbeat(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    spool = tmp_path / "events.jsonl"
    spool.write_text(navigation_events(), encoding="utf-8")
    output = tmp_path / "output"
    monkeypatch.setattr("runtime.desktop_health", health)
    captures: list[WindowIdentity] = []

    def fake_capture(_self: NativeWindowCapture, selected: WindowIdentity) -> CapturedFrame:
        captures.append(selected)
        return CapturedFrame(b"jpeg", 1, 1, NOW)

    monkeypatch.setattr("runtime.NativeWindowCapture.capture", fake_capture)
    monkeypatch.setattr("runtime.select_window", target)
    broker = ActivityBroker(RunConfig(spool, tmp_path, output, screen_policy=ScreenPolicy.APP_WINDOW), FixedClock())
    assert broker.window_store is not None
    broker.window_store.share(target(tmp_path, 42))
    broker.step(NOW)
    first = ActivityEvent.model_validate_json((output / "activity.json").read_text(encoding="utf-8"))
    broker.step(NOW + 250)
    second = ActivityEvent.model_validate_json((output / "activity.json").read_text(encoding="utf-8"))
    assert second.seq > first.seq
    assert len(captures) == 2
    broker.reader.close()
