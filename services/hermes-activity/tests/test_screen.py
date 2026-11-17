from __future__ import annotations

from collections.abc import Mapping
import hashlib
import os
from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from activity_models import ActivityEvent
from broker import ActivityBroker, RunConfig
from hermes_feed import SpoolEvent
from screen import CapturedFrame, DesktopHealth, ScreenPolicy, desktop_health

NOW = 1_700_000_000_000


def metadata_health(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, create_time: object, cmdline: object
) -> DesktopHealth:
    desktop = tmp_path / "bot-desktop"
    desktop.mkdir(mode=0o700)
    authority = desktop / "xauth"
    authority.write_bytes(b"x")
    authority.chmod(0o600)
    env_path = desktop / "env"
    env_path.write_text(f"DISPLAY=:20\nXAUTHORITY={authority}\n", encoding="utf-8")
    env_path.chmod(0o600)
    pid_path = desktop / "launcher.pid"
    pid_path.write_text("12345", encoding="utf-8")
    pid_path.chmod(0o600)
    observed_pids: list[int] = []

    class FakeProcess:
        def __init__(self, pid: int) -> None:
            observed_pids.append(pid)

        def create_time(self) -> object:
            return create_time

        def cmdline(self) -> object:
            return cmdline

    def fake_kill(pid: int, signal: int) -> None:
        assert (pid, signal) == (12345, 0)

    monkeypatch.setattr("screen.psutil.Process", FakeProcess)
    monkeypatch.setattr("screen.os.kill", fake_kill)
    result = desktop_health(tmp_path)
    assert observed_pids == [12345]
    return result


@pytest.mark.parametrize("create_time", [1_700_000_000, 1_700_000_000.125])
@pytest.mark.parametrize("cmdline", [["python", "launcher.py", "--flag"], ["BOT-DESKTOP", "--flag"]])
def test_valid_native_launcher_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, create_time: float, cmdline: list[str]
) -> None:
    result = metadata_health(tmp_path, monkeypatch, create_time, cmdline)
    identity_hash = hashlib.sha256(" ".join(cmdline).encode()).hexdigest()
    assert result.alive
    assert result.generation == f"12345:{create_time:.3f}:{identity_hash}::20"


@pytest.mark.parametrize(
    "create_time",
    [True, False, None, "1700000000", 10**400, float("nan"), float("inf"), float("-inf"), 0, -1],
)
def test_malformed_native_creation_time_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, create_time: object
) -> None:
    result = metadata_health(tmp_path, monkeypatch, create_time, ["launcher"])
    assert not result.alive
    assert result.generation is None


@pytest.mark.parametrize(
    "cmdline", [None, "launcher", ("launcher",), ["launcher", None], ["launcher", 1], [], [""], ["python"]]
)
def test_malformed_native_command_line_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cmdline: object
) -> None:
    result = metadata_health(tmp_path, monkeypatch, 1_700_000_000, cmdline)
    assert not result.alive
    assert result.generation is None


class FixedClock:
    def now_ms(self) -> int:
        return NOW

    def sleep(self, seconds: float) -> None:
        del seconds


def health(_profile_home: Path) -> DesktopHealth:
    return DesktopHealth(True, {"DISPLAY": ":1", "XAUTHORITY": "/tmp/bot.xauth"}, "generation-1")


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

    def fake_capture(_env: Mapping[str, str]) -> CapturedFrame:
        return CapturedFrame(b"jpeg", 1, 1, NOW)

    monkeypatch.setattr("runtime.capture_frame", fake_capture)

    ActivityBroker(
        RunConfig(spool, tmp_path, output, once=True, screen_policy=ScreenPolicy.BOT_DESKTOP), FixedClock()
    ).run()
    event = ActivityEvent.model_validate_json((output / "activity.json").read_text(encoding="utf-8"))
    assert event.payload.screen.state == "live"
    assert event.payload.screen.filename in {"hermes-screen-0.jpg", "hermes-screen-1.jpg"}
    assert event.payload.screen.width <= 1_280
    assert event.payload.screen.height <= 800
    assert event.payload.screen.ttl_ms == 2_000
    assert (output / "hermes-screen-1.jpg").is_file()


def test_sensitive_event_appended_during_capture_is_discarded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    spool = tmp_path / "events.jsonl"
    spool.write_text(navigation_events(), encoding="utf-8")
    output = tmp_path / "output"

    def capture(_env: Mapping[str, str]) -> CapturedFrame:
        with spool.open("a", encoding="utf-8") as stream:
            stream.write(
                SpoolEvent(
                    kind="tool",
                    ts_ms=NOW,
                    session="s",
                    phase="running",
                    category="BROWSER",
                    action="typing",
                    detail="text hidden",
                    call="secret",
                    shutter=True,
                ).model_dump_json()
                + "\n"
            )
        return CapturedFrame(b"jpeg", 1, 1, NOW)

    monkeypatch.setattr("runtime.desktop_health", health)
    monkeypatch.setattr("runtime.capture_frame", capture)

    ActivityBroker(
        RunConfig(spool, tmp_path, output, once=True, screen_policy=ScreenPolicy.BOT_DESKTOP), FixedClock()
    ).run()
    event = ActivityEvent.model_validate_json((output / "activity.json").read_text(encoding="utf-8"))
    assert event.payload.screen.state == "shuttered"
    assert not (output / "hermes-screen-1.jpg").exists()


def test_new_frame_is_published_before_heartbeat(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    spool = tmp_path / "events.jsonl"
    spool.write_text(navigation_events(), encoding="utf-8")
    output = tmp_path / "output"
    monkeypatch.setattr("runtime.desktop_health", health)
    captures: list[Mapping[str, str]] = []

    def fake_capture(_env: Mapping[str, str]) -> CapturedFrame:
        captures.append(_env)
        return CapturedFrame(b"jpeg", 1, 1, NOW)

    monkeypatch.setattr("runtime.capture_frame", fake_capture)
    broker = ActivityBroker(RunConfig(spool, tmp_path, output, screen_policy=ScreenPolicy.BOT_DESKTOP), FixedClock())
    broker.step(NOW)
    first = ActivityEvent.model_validate_json((output / "activity.json").read_text(encoding="utf-8"))
    broker.step(NOW + 250)
    second = ActivityEvent.model_validate_json((output / "activity.json").read_text(encoding="utf-8"))
    assert second.seq > first.seq
    assert len(captures) == 2
    broker.reader.close()
