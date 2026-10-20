from __future__ import annotations

import fcntl
import os
from collections.abc import Callable
from pathlib import Path
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "plugin"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hermes_feed import SpoolEvent
from cursor import CursorSnapshot, IncrementalSpoolReader
from furbomek_stream import observer


def test_sensitive_pre_hook_appends_before_return(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    spool = tmp_path / "events.jsonl"
    monkeypatch.setenv("FURBOMEK_ACTIVITY_SPOOL", str(spool))

    result = observer.on_pre_tool_call(
        tool_name="browser_type",
        args={"text": "secret"},
        session_id="s",
        tool_call_id="call-1",
    )

    assert result is None
    document = SpoolEvent.model_validate_json(spool.read_text(encoding="utf-8"))
    assert document.kind == "tool"
    assert document.phase == "running"
    assert document.shutter
    assert document.call == "call-1"
    assert "secret" not in spool.read_text(encoding="utf-8")


def test_malformed_completion_is_bounded_and_observer_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    spool = tmp_path / "events.jsonl"
    monkeypatch.setenv("FURBOMEK_ACTIVITY_SPOOL", str(spool))

    result = observer.on_post_tool_call(
        tool_name="browser_type",
        args={"text": "secret"},
        session_id="s",
        tool_call_id="call-1",
        duration_ms=float("nan"),
        status="error",
        error_type="failure",
    )

    assert result is None
    document = SpoolEvent.model_validate_json(spool.read_text(encoding="utf-8"))
    assert document.phase == "error"
    assert document.duration_ms == 0
    assert spool.stat().st_mode & 0o777 == 0o600
    assert spool.parent.stat().st_mode & 0o777 == 0o700


def test_register_only_installs_observer_hooks() -> None:
    class Context:
        def __init__(self) -> None:
            self.names: list[str] = []

        def register_hook(self, name: str, callback: Callable[..., None]) -> None:
            del callback
            self.names.append(name)

    context = Context()
    observer.register(context)
    assert context.names == [
        "pre_tool_call",
        "post_tool_call",
        "pre_llm_call",
        "post_llm_call",
        "on_session_start",
        "on_session_end",
        "pre_approval_request",
        "post_approval_response",
    ]


def test_append_failure_leaves_cursor_observable_failure_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    spool = tmp_path / "events.jsonl"
    monkeypatch.setenv("FURBOMEK_ACTIVITY_SPOOL", str(spool))

    def fail(_draft: observer.EventDraft) -> None:
        raise OSError

    monkeypatch.setattr(observer, "_append", fail)
    observer.on_pre_tool_call(tool_name="browser_type", session_id="s", tool_call_id="call")
    assert b"observer_failure" in spool.read_bytes()
    reader = IncrementalSpoolReader(spool, CursorSnapshot(None, 0))
    result = reader.poll()
    assert result.uncertain
    reader.close()


def test_lock_contention_returns_without_waiting_for_hermes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    spool = tmp_path / "events.jsonl"
    monkeypatch.setenv("FURBOMEK_ACTIVITY_SPOOL", str(spool))
    lock_path = spool.with_name(f".{spool.name}.lock")
    lock_path.write_bytes(b"")
    lock_path.chmod(0o600)
    fd = os.open(lock_path, os.O_RDWR)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        observer.on_pre_tool_call(tool_name="browser_type", session_id="s", tool_call_id="blocked")
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
