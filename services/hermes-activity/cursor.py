"""Incremental binary cursor for the Hermes JSONL spool."""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from typing import TYPE_CHECKING, BinaryIO

if TYPE_CHECKING:
    from pathlib import Path

from hermes_feed import MAX_LINE_BYTES, SpoolEvent, parse_complete_line

MAX_POLL_BYTES = 65_536


@dataclass(frozen=True, slots=True)
class CursorSnapshot:
    """Persisted inode and byte offset."""

    inode: int | None
    offset: int


@dataclass(frozen=True, slots=True)
class PollResult:
    """Events and continuity facts produced by one cursor poll."""

    events: tuple[SpoolEvent, ...]
    cursor: CursorSnapshot
    readable: bool
    gap: bool
    uncertain: bool


class IncrementalSpoolReader:
    """Read complete records once while draining rotations in order."""

    path: Path
    _fd: BinaryIO | None
    _inode: int | None
    _offset: int
    _read_offset: int
    _pending: bytes
    _discarding_oversize: bool
    _poll_gap: bool
    _poll_uncertain: bool

    def __init__(self, path: Path, snapshot: CursorSnapshot) -> None:
        """Open lazily so a missing spool remains a recoverable boundary fact."""
        self.path = path
        self._fd = None
        self._inode = snapshot.inode
        self._offset = max(0, snapshot.offset)
        self._read_offset = self._offset
        self._pending = b""
        self._discarding_oversize = False
        self._poll_gap = False
        self._poll_uncertain = False

    def poll(self) -> PollResult:
        """Consume newly complete records and advance the durable cursor."""
        events: list[SpoolEvent] = []
        self._poll_gap = False
        self._poll_uncertain = False
        self._consume_failure_marker()
        readable = self._ensure_open()
        if readable:
            self._drain_current(events)
            if self._path_rotated():
                readable = self._switch_to_new_path(events)
        return PollResult(
            tuple(events), CursorSnapshot(self._inode, self._offset), readable, self._poll_gap, self._poll_uncertain
        )

    def _consume_failure_marker(self) -> None:
        marker = self.path.with_suffix(".failure")
        try:
            marker.lstat()
        except FileNotFoundError:
            return
        except OSError:
            self._poll_uncertain = True
            return
        try:
            marker.unlink()
        except OSError:
            self._poll_uncertain = True
        else:
            self._poll_uncertain = True

    def close(self) -> None:
        """Close the held descriptor."""
        if self._fd is not None:
            self._fd.close()
            self._fd = None

    def _ensure_open(self) -> bool:
        if self._fd is not None:
            try:
                os.fstat(self._fd.fileno())
            except OSError:
                self._poll_uncertain = True
                return False
            return True
        try:
            self._fd = self.path.open("rb")
            inode = os.fstat(self._fd.fileno()).st_ino
        except OSError:
            self._poll_gap = self._inode is not None
            self._poll_uncertain = True
            return False
        if self._inode is None:
            self._offset = 0
        elif inode != self._inode:
            self._offset = 0
            self._read_offset = 0
            self._poll_gap = True
            self._poll_uncertain = True
        self._inode = inode
        return True

    def _path_rotated(self) -> bool:
        if self._fd is None:
            return False
        try:
            # Drain an old generation over bounded polls before switching paths.
            return self._read_offset >= os.fstat(self._fd.fileno()).st_size and self.path.stat().st_ino != self._inode
        except OSError:
            self._poll_uncertain = True
            return False

    def _switch_to_new_path(self, events: list[SpoolEvent]) -> bool:
        if self._pending or self._discarding_oversize:
            self._poll_gap = True
            self._poll_uncertain = True
        self._close_current()
        self._pending = b""
        self._discarding_oversize = False
        self._offset = 0
        self._read_offset = 0
        self._inode = None
        readable = self._ensure_open()
        if self._fd is not None:
            self._drain_current(events)
        return readable

    def _close_current(self) -> None:
        if self._fd is not None:
            self._fd.close()
            self._fd = None

    def _drain_current(self, events: list[SpoolEvent]) -> None:
        if self._fd is None:
            return
        try:
            size = os.fstat(self._fd.fileno()).st_size
            if size < self._read_offset:
                self._offset = 0
                self._read_offset = 0
                self._pending = b""
                self._discarding_oversize = False
                self._poll_gap = True
                self._poll_uncertain = True
            self._fd.seek(self._read_offset)
            chunk = self._fd.read(MAX_POLL_BYTES)
        except OSError:
            self._poll_uncertain = True
            return
        if not chunk:
            return
        self._read_offset += len(chunk)
        self._pending += chunk
        self._consume_complete(events)

    def _consume_complete(self, events: list[SpoolEvent]) -> None:
        while True:
            if self._discarding_oversize:
                newline = self._pending.find(b"\n")
                if newline < 0:
                    self._pending = b""
                    return
                self._offset = self._read_offset - len(self._pending) + newline + 1
                self._pending = self._pending[newline + 1 :]
                self._discarding_oversize = False
            newline = self._pending.find(b"\n")
            if newline < 0:
                if len(self._pending) > MAX_LINE_BYTES:
                    self._discarding_oversize = True
                    self._poll_uncertain = True
                    self._pending = b""
                return
            line = self._pending[: newline + 1]
            self._pending = self._pending[newline + 1 :]
            self._offset += len(line)
            event = parse_complete_line(line)
            if event is None or (event.kind == "character" and not self._character_source_authorized()):
                self._poll_uncertain = True
            else:
                events.append(event)

    def _character_source_authorized(self) -> bool:
        """Admit character rows only from a current-UID private regular spool."""
        if self._fd is None:
            return False
        try:
            source = os.fstat(self._fd.fileno())
            current = self.path.lstat()
            parent = self.path.parent.lstat()
        except OSError:
            return False
        return (
            stat.S_ISREG(source.st_mode)
            and stat.S_ISREG(current.st_mode)
            and stat.S_ISDIR(parent.st_mode)
            and source.st_ino == current.st_ino
            and source.st_dev == current.st_dev
            and source.st_uid == os.getuid()
            and parent.st_uid == os.getuid()
            and not (source.st_mode & 0o077)
            and not (parent.st_mode & 0o077)
        )
