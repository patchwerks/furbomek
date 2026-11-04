from __future__ import annotations

import errno
import fcntl
import os
from collections.abc import Callable
from pathlib import Path
import sys
import time

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


@pytest.mark.parametrize("status", ["ok", "error"])
def test_observer_lifecycle_spool_reader_integration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, status: str
) -> None:
    # Synthetic offline lifecycle; not actual Hermes runtime qualification.
    tmp_path.chmod(0o700)
    spool = tmp_path / "events.jsonl"
    monkeypatch.setenv("FURBOMEK_ACTIVITY_SPOOL", str(spool))
    session_id = f"fixture-session-{status}"
    tool_call_id = f"fixture-call-{status}"
    synthetic_secret = "fixture-private-argument-6a82"
    synthetic_result_secret = "fixture-private-result-9b73"

    assert observer.on_session_start(session_id=session_id) is None
    assert observer.on_pre_llm_call(session_id=session_id) is None
    assert (
        observer.on_pre_tool_call(
            tool_name="browser_type",
            args={"text": synthetic_secret},
            session_id=session_id,
            tool_call_id=tool_call_id,
        )
        is None
    )
    assert (
        observer.on_post_tool_call(
            tool_name="browser_type",
            args={"text": synthetic_secret},
            session_id=session_id,
            tool_call_id=tool_call_id,
            result=synthetic_result_secret,
            status=status,
            duration_ms=37,
        )
        is None
    )
    assert observer.on_post_llm_call(session_id=session_id) is None
    assert observer.on_session_end(session_id=session_id) is None

    raw = spool.read_bytes()
    assert synthetic_secret.encode() not in raw
    assert synthetic_result_secret.encode() not in raw
    assert b'"args"' not in raw
    assert b'"arguments"' not in raw
    assert b'"result"' not in raw
    assert b'"results"' not in raw

    reader = IncrementalSpoolReader(spool, CursorSnapshot(None, 0))
    try:
        result = reader.poll()
        assert not result.gap
        assert not result.uncertain
        assert len(result.events) == 6
        assert [event.kind for event in result.events] == [
            "session_start",
            "thinking",
            "tool",
            "tool",
            "turn_done",
            "session_end",
        ]
        assert all(event.session == session_id for event in result.events)
        running, completion = result.events[2:4]
        assert [running.phase, completion.phase] == ["running", status]
        assert running.call == tool_call_id
        assert completion.call == tool_call_id
        assert completion.duration_ms == 37
        assert not reader.poll().events
    finally:
        reader.close()


@pytest.mark.parametrize(
    ("failed", "interrupted", "phase"),
    [
        (False, False, "ok"),
        (True, False, "error"),
        (False, True, "interrupted"),
        (True, True, "error"),
        ("yes", 1, "ok"),
    ],
)
def test_end_metadata_is_boolean_only_and_redacted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failed: bool | str, interrupted: bool | int, phase: str
) -> None:
    spool = tmp_path / "events.jsonl"
    monkeypatch.setenv("FURBOMEK_ACTIVITY_SPOOL", str(spool))
    assert (
        observer.on_session_end(
            session_id="selected",
            failed=failed,
            interrupted=interrupted,
            turn_exit_reason="private-reason-canary",
            error="private-error-canary",
            body="private-body-canary",
        )
        is None
    )
    raw = spool.read_text()
    row = SpoolEvent.model_validate_json(raw)
    assert row.kind == "session_end"
    assert row.phase == phase
    assert "private-" not in raw


@pytest.mark.parametrize("target_name", ["events.jsonl", ".events.jsonl.lock"])
def test_fifo_spool_or_lock_returns_with_truthful_failure_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, target_name: str
) -> None:
    tmp_path.chmod(0o700)
    spool = tmp_path / "events.jsonl"
    target = tmp_path / target_name
    os.mkfifo(target, 0o600)
    before = target.lstat()
    monkeypatch.setenv("FURBOMEK_ACTIVITY_SPOOL", str(spool))
    started = time.monotonic()

    assert observer.on_pre_llm_call(session_id="fifo-fixture") is None

    assert time.monotonic() - started < 1.0
    after = target.lstat()
    assert (after.st_ino, after.st_mode, after.st_size) == (before.st_ino, before.st_mode, before.st_size)
    assert spool.with_suffix(".failure").read_bytes() == b'{"observer_failure":true}\n'
    assert not spool.with_suffix(".old").exists()
    if target != spool:
        assert not spool.exists()


@pytest.mark.parametrize("target_name", ["events.jsonl", ".events.jsonl.lock"])
def test_hardlinked_spool_or_lock_does_not_mutate_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, target_name: str
) -> None:
    tmp_path.chmod(0o700)
    spool = tmp_path / "events.jsonl"
    destination = tmp_path / "owner-private-data"
    destination.write_bytes(b"unchanged-private-canary\n")
    destination.chmod(0o600)
    target = tmp_path / target_name
    target.hardlink_to(destination)
    before = destination.stat()
    monkeypatch.setenv("FURBOMEK_ACTIVITY_SPOOL", str(spool))

    assert observer.on_pre_llm_call(session_id="hardlink-fixture") is None

    after = destination.stat()
    assert destination.read_bytes() == b"unchanged-private-canary\n"
    assert (after.st_ino, after.st_nlink, after.st_mode, after.st_mtime_ns) == (
        before.st_ino,
        before.st_nlink,
        before.st_mode,
        before.st_mtime_ns,
    )
    assert target.stat().st_ino == before.st_ino
    assert spool.with_suffix(".failure").read_bytes() == b'{"observer_failure":true}\n'
    assert not spool.with_suffix(".old").exists()
    if target != spool:
        assert not spool.exists()


@pytest.mark.parametrize("write_result", [0, -1])
def test_nonprogress_write_fails_once_and_emits_failure_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, write_result: int
) -> None:
    spool = tmp_path / "events.jsonl"
    monkeypatch.setenv("FURBOMEK_ACTIVITY_SPOOL", str(spool))
    real_write = os.write
    event_writes = 0

    def stalled_write(fd: int, payload: bytes) -> int:
        nonlocal event_writes
        if b'"kind":"thinking"' in payload:
            event_writes += 1
            assert event_writes == 1, "observer retried a write without progress"
            return write_result
        return real_write(fd, payload)

    with monkeypatch.context() as patch:
        patch.setattr(os, "write", stalled_write)
        assert observer.on_pre_llm_call(session_id="write-fixture") is None

    assert event_writes == 1
    assert spool.read_bytes() == b'{"observer_failure":true}\n'
    assert not spool.with_suffix(".failure").exists()
    reader = IncrementalSpoolReader(spool, CursorSnapshot(None, 0))
    try:
        assert reader.poll().uncertain
    finally:
        reader.close()


def test_failed_rotation_does_not_close_reused_descriptor(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    spool = tmp_path / "events.jsonl"
    spool.write_bytes(b"original\n")
    spool.chmod(0o600)
    sentinel = tmp_path / "sentinel"
    sentinel.write_bytes(b"preserved\n")
    sentinel_fds: list[int] = []

    def failing_replace(path: Path, target: str | os.PathLike[str]) -> Path:
        assert path == spool
        assert Path(target) == spool.with_suffix(".old")
        # Reuse the descriptor just closed for rotation. A stale finally-close
        # would close this unrelated, newly owned descriptor.
        sentinel_fds.append(os.open(sentinel, os.O_RDONLY))
        message = "injected rotation failure"
        raise OSError(message)

    try:
        with monkeypatch.context() as patch:
            patch.setattr(observer, "_MAX_SPOOL_BYTES", 1)
            patch.setattr(Path, "replace", failing_replace)
            with pytest.raises(OSError, match="injected rotation failure"):
                observer._append_bytes(spool, b"new\n")  # pyright: ignore[reportPrivateUsage]
        assert len(sentinel_fds) == 1
        assert os.fstat(sentinel_fds[0]).st_ino == sentinel.stat().st_ino
        assert os.read(sentinel_fds[0], 32) == b"preserved\n"
        assert spool.read_bytes() == b"original\n"
        assert not spool.with_suffix(".old").exists()
    finally:
        for fd in sentinel_fds:
            try:
                os.close(fd)
            except OSError as exc:
                if exc.errno != errno.EBADF:
                    raise


def test_secure_open_closes_descriptor_on_fstat_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    spool = tmp_path / "events.jsonl"
    observed_fds: list[int] = []

    def failing_fstat(fd: int) -> os.stat_result:
        observed_fds.append(fd)
        message = "injected fstat failure"
        raise OSError(message)

    with monkeypatch.context() as patch:
        patch.setattr(os, "fstat", failing_fstat)
        with pytest.raises(OSError, match="injected fstat failure"):
            observer._secure_open(spool)  # pyright: ignore[reportPrivateUsage]

    assert len(observed_fds) == 1
    with pytest.raises(OSError, match=r".+") as raised:
        os.fstat(observed_fds[0])
    assert raised.value.errno == errno.EBADF
