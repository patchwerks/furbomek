"""Observer-only Hermes hooks with bounded synchronous spool writes."""

from __future__ import annotations

import fcntl
import json
import os
import stat
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final, Protocol

if TYPE_CHECKING:
    from collections.abc import Callable

from .projection import JsonValue, PublicAction, outcome, project_tool

_SPOOL_ENV: Final = "FURBOMEK_ACTIVITY_SPOOL"
_MAX_SPOOL_BYTES: Final = 4 * 1024 * 1024
_MAX_RECORD_BYTES: Final = 4_096
_FAILURE_MARKER: Final = b'{"observer_failure":true}\n'


@dataclass(frozen=True, slots=True)
class EventDraft:
    """Bounded event values ready for one synchronous append."""

    kind: str
    session: str
    phase: str = "ok"
    category: str = "AGENT"
    action: str = "using a tool"
    detail: str = ""
    call: str = ""
    shutter: bool = False
    duration_ms: int = 0
    privacy_release: bool = False


class HookContext(Protocol):
    """Minimal Hermes registration contract."""

    def register_hook(self, name: str, callback: Callable[..., None]) -> None:
        """Register one observer callback."""
        ...


def _spool_path() -> Path:
    configured = os.environ.get(_SPOOL_ENV)
    if configured:
        return Path(configured)
    return Path(f"/dev/shm/furbomek-hermes-{os.getuid()}") / "events.jsonl"


def _secure_directory(path: Path) -> None:
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    metadata = path.lstat()
    if path.is_symlink() or not path.is_dir() or metadata.st_uid != os.getuid() or metadata.st_mode & 0o077:
        raise OSError("activity spool directory is not owner-only")


def _secure_open(path: Path) -> int:
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    metadata = os.fstat(fd)
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid() or metadata.st_mode & 0o077:
        os.close(fd)
        raise OSError("activity spool file is not owner-only")
    return fd


def _write_all(fd: int, payload: bytes) -> None:
    written = 0
    while written < len(payload):
        written += os.write(fd, payload[written:])


def _append_bytes(path: Path, payload: bytes) -> None:
    _secure_directory(path.parent)
    lock_path = path.with_name(f".{path.name}.lock")
    lock_fd = _secure_open(lock_path)
    locked = False
    try:
        for _attempt in range(3):
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                continue
            locked = True
            break
        if not locked:
            raise BlockingIOError("activity spool lock is busy")
        spool_fd = _secure_open(path)
        try:
            if os.fstat(spool_fd).st_size > _MAX_SPOOL_BYTES:
                os.close(spool_fd)
                path.replace(path.with_suffix(".old"))
                spool_fd = _secure_open(path)
            _write_all(spool_fd, payload)
        finally:
            os.close(spool_fd)
    finally:
        if locked:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)


def _failure_marker(path: Path) -> None:
    try:
        _append_bytes(path, _FAILURE_MARKER)
    except OSError:
        try:
            _append_bytes(path.with_suffix(".failure"), _FAILURE_MARKER)
        except OSError:
            return


def _append(draft: EventDraft) -> None:
    payload: dict[str, JsonValue] = {
        "v": 1,
        "kind": draft.kind,
        "ts_ms": int(time.time() * 1000),
        "session": draft.session,
        "phase": draft.phase,
        "category": draft.category,
        "action": draft.action,
        "detail": draft.detail,
        "call": draft.call,
        "shutter": draft.shutter,
        "duration_ms": draft.duration_ms,
    }
    if draft.privacy_release:
        payload["privacy_release"] = True
    line = json.dumps(payload, separators=(",", ":")).encode("utf-8") + b"\n"
    if len(line) > _MAX_RECORD_BYTES:
        raise OSError("observer event exceeds record limit")
    _append_bytes(_spool_path(), line)


def _emit(draft: EventDraft) -> None:
    try:
        _append(draft)
    except OSError:
        _failure_marker(_spool_path())


def _bounded(value: JsonValue, limit: int) -> str:
    return value[:limit] if isinstance(value, str) else ""


def _duration(value: JsonValue) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0
    try:
        return max(0, min(int(value), 86_400_000))
    except (OverflowError, ValueError):
        return 0


def _draft(
    kind: str,
    session_id: JsonValue,
    public: PublicAction,
    *,
    phase: str = "ok",
    call: JsonValue = "",
    duration_ms: JsonValue = 0,
    privacy_release: bool = False,
) -> EventDraft:
    return EventDraft(
        kind=kind,
        session=_bounded(session_id, 64),
        phase=phase,
        category=public.category,
        action=public.action,
        detail=public.detail,
        call=_bounded(call, 64),
        shutter=public.shutter,
        duration_ms=_duration(duration_ms),
        privacy_release=privacy_release,
    )


def on_pre_tool_call(
    *,
    tool_name: str = "",
    args: JsonValue | None = None,
    task_id: str = "",
    session_id: str = "",
    tool_call_id: str = "",
    turn_id: str = "",
    api_request_id: str = "",
    **_ignored: JsonValue,
) -> None:
    """Record a pre-tool observation synchronously before execution."""
    del task_id, turn_id, api_request_id
    public = project_tool(tool_name, args if args is not None else {})
    _emit(_draft("tool", session_id, public, phase="running", call=tool_call_id))


def on_post_tool_call(
    *,
    tool_name: str = "",
    args: JsonValue | None = None,
    result: JsonValue | None = None,
    task_id: str = "",
    session_id: str = "",
    tool_call_id: str = "",
    turn_id: str = "",
    api_request_id: str = "",
    duration_ms: JsonValue = 0,
    status: JsonValue = None,
    error_type: JsonValue = None,
    **_ignored: JsonValue,
) -> None:
    """Record a bounded completion observation synchronously."""
    del result, task_id, turn_id, api_request_id
    public = project_tool(tool_name, args if args is not None else {})
    final_status = outcome(status, error_type)
    _emit(
        _draft(
            "tool",
            session_id,
            public,
            phase=final_status,
            call=tool_call_id,
            duration_ms=duration_ms,
            privacy_release=final_status == "ok" and public.privacy_release,
        )
    )


def on_pre_llm_call(*, session_id: str = "", **_ignored: JsonValue) -> None:
    """Record the start of a model turn."""
    _emit(EventDraft("thinking", _bounded(session_id, 64)))


def on_post_llm_call(*, session_id: str = "", **_ignored: JsonValue) -> None:
    """Record the end of a model turn."""
    _emit(EventDraft("turn_done", _bounded(session_id, 64)))


def on_session_start(*, session_id: str = "", **_ignored: JsonValue) -> None:
    """Record a session start."""
    _emit(EventDraft("session_start", _bounded(session_id, 64)))


def on_session_end(
    *, session_id: str = "", failed: JsonValue = False, interrupted: JsonValue = False, **_ignored: JsonValue
) -> None:
    """Record only bounded Boolean end metadata, never raw reasons."""
    phase = "error" if failed is True else "interrupted" if interrupted is True else "ok"
    _emit(EventDraft("session_end", _bounded(session_id, 64), phase=phase))


def on_pre_approval(*, session_key: str = "", **_ignored: JsonValue) -> None:
    """Record an approval request."""
    _emit(EventDraft("approval", _bounded(session_key, 64), phase="waiting"))


def on_post_approval(*, session_key: str = "", **_ignored: JsonValue) -> None:
    """Record an approval response."""
    _emit(EventDraft("approval", _bounded(session_key, 64), phase="resolved"))


def register(ctx: HookContext) -> None:
    """Register only read-only lifecycle hooks supported by Hermes."""
    for name, callback in (
        ("pre_tool_call", on_pre_tool_call),
        ("post_tool_call", on_post_tool_call),
        ("pre_llm_call", on_pre_llm_call),
        ("post_llm_call", on_post_llm_call),
        ("on_session_start", on_session_start),
        ("on_session_end", on_session_end),
        ("pre_approval_request", on_pre_approval),
        ("post_approval_response", on_post_approval),
    ):
        ctx.register_hook(name, callback)
