from __future__ import annotations

from pathlib import Path
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from activity_models import ActivityEvent
from broker import ActivityBroker, RunConfig
from screen import CapturedFrame, DesktopHealth, ScreenPolicy
from window_capture import NativeWindowCapture, WindowIdentity
from hermes_feed import SpoolEvent


NOW = 1_700_000_000_000


class FixedClock:
    def now_ms(self) -> int:
        return NOW

    def sleep(self, seconds: float) -> None:
        del seconds


def test_explicit_app_window_consent_survives_sensitive_observer_event(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    identity = WindowIdentity(42, 100, 1000, 12.5, ":20", "desktop-generation", 800, 600, "browser", "Browser")
    spool = tmp_path / "events.jsonl"
    spool.write_text("", encoding="utf-8")

    def fake_health(_profile: Path) -> DesktopHealth:
        return DesktopHealth(True, {"DISPLAY": ":20"}, "desktop-generation")

    monkeypatch.setattr("runtime.desktop_health", fake_health)

    def fake_select(_profile: Path, _window_id: int) -> WindowIdentity:
        return identity

    def fake_capture(_capture: NativeWindowCapture, _target: WindowIdentity) -> CapturedFrame:
        return CapturedFrame(b"jpeg", 800, 600, NOW)

    monkeypatch.setattr("runtime.select_window", fake_select)
    monkeypatch.setattr("runtime.NativeWindowCapture.capture", fake_capture)

    broker = ActivityBroker(
        RunConfig(spool, tmp_path / "profile", tmp_path / "output", once=True, screen_policy=ScreenPolicy.APP_WINDOW),
        FixedClock(),
    )
    assert broker.window_store is not None
    broker.window_store.share(identity)
    spool.write_text(
        SpoolEvent(
            kind="tool",
            ts_ms=NOW,
            session="s",
            call="sensitive",
            phase="running",
            category="BROWSER",
            action="typing",
            detail="text hidden",
            shutter=True,
        ).model_dump_json()
        + "\n",
        encoding="utf-8",
    )
    broker.step(NOW)
    event = ActivityEvent.model_validate_json((tmp_path / "output" / "activity.json").read_text(encoding="utf-8"))

    assert event.payload.screen.state == "live"
    assert (tmp_path / "output" / "hermes-screen-1.jpg").is_file()
    broker.reader.close()
