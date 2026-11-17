"""Owner-only, restart-safe consent for one selected X11 application window."""

from __future__ import annotations

import fcntl
import os
import secrets
import stat
import time
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, Final, override

from pydantic import BaseModel, ConfigDict, Field

from activity_models import ActivityEvent
from screen import invalidate_frames, offline_screen

if TYPE_CHECKING:
    from window_capture import WindowIdentity

CONSENT_NAME: Final = "window-consent.json"
LOCK_NAME: Final = "window-consent.lock"


class ConsentMode(StrEnum):
    """Whether the selected window may produce pixels."""

    SHUTTERED = "shuttered"
    SHARED = "shared"


class ConsentError(ValueError):
    """A selected-window consent operation failed closed."""

    reason: str

    def __init__(self, reason: str) -> None:
        """Create a fail-closed consent error with an operator-facing reason."""
        super().__init__(reason)
        self.reason = reason

    @override
    def __str__(self) -> str:
        return self.reason


class ConsentDocument(BaseModel):
    """Persisted consent capability and its identity binding."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid", strict=True)

    schema_version: str = Field(default="furbomek.window-consent.v1", pattern=r"^furbomek\.window-consent\.v1$")
    owner_uid: int = Field(ge=0)
    boot_nonce: str = Field(min_length=32, max_length=64)
    generation: int = Field(ge=0)
    mode: ConsentMode
    display: str | None = None
    profile_generation: str | None = None
    window_id: int | None = Field(default=None, ge=1)
    pid: int | None = Field(default=None, ge=1)
    uid: int | None = Field(default=None, ge=0)
    process_start_time: float | None = Field(default=None, ge=0)
    width: int | None = Field(default=None, ge=1, le=4096)
    height: int | None = Field(default=None, ge=1, le=4096)

    def matches(self, target: WindowIdentity) -> bool:
        """Check every identity-bearing capability field, not merely its XID."""
        return (
            self.owner_uid == os.getuid()
            and self.window_id == target.window_id
            and self.pid == target.pid
            and self.uid == target.uid
            and self.process_start_time == target.process_start_time
            and self.display == target.display
            and self.profile_generation == target.profile_generation
            and self.width == target.width
            and self.height == target.height
        )


@dataclass(frozen=True, slots=True)
class WindowConsentStore:
    """Serialize operator actions and frame publication for one output root."""

    profile_home: Path
    out_dir: Path
    lock_timeout_s: float = 2.0

    @property
    def path(self) -> Path:
        """Return the private consent document path."""
        return self.out_dir / CONSENT_NAME

    @property
    def lock_path(self) -> Path:
        """Return the private consent lock path."""
        return self.out_dir / LOCK_NAME

    def boot(self) -> ConsentDocument:
        """Create a fresh broker nonce and shutter any previous capability."""
        with self.locked():
            current = self._read_unlocked()
            self.clear_public_locked()
            return self._write_unlocked(self._shuttered(current, secrets.token_hex(24)))

    def share(self, identity: WindowIdentity) -> ConsentDocument:
        """Bind explicit consent to the currently validated target identity."""
        with self.locked():
            current = self._read_unlocked()
            base = current or self._initial()
            self.clear_public_locked()
            return self._write_unlocked(self._from_identity(base, identity, ConsentMode.SHARED))

    def resume(self, identity: WindowIdentity) -> ConsentDocument:
        """Resume only after the operator supplies a freshly validated identity."""
        with self.locked():
            current = self._read_unlocked()
            if current is None or current.window_id is None:
                raise ConsentError("no selected window is available to resume")
            self.clear_public_locked()
            return self._write_unlocked(self._from_identity(current, identity, ConsentMode.SHARED))

    def shutter(self) -> ConsentDocument:
        """Revoke the capability and increment its monotonic generation."""
        with self.locked():
            return self.revoke_locked()

    def revoke_locked(self) -> ConsentDocument:
        """Revoke under the publication lock, including on a capture identity failure."""
        current = self._read_unlocked()
        document = self._write_unlocked(
            self._shuttered(current, current.boot_nonce if current else secrets.token_hex(24))
        )
        self.clear_public_locked()
        return document

    def clear_public_locked(self) -> None:
        """Acknowledge revocation only after deleting pixels and clearing metadata."""
        invalidate_frames(self.out_dir)
        public = self.out_dir / "activity.json"
        if public.exists():
            event = ActivityEvent.model_validate_json(public.read_bytes())
            screen = event.payload.screen
            seq = 0 if screen is None else screen.seq
            payload = event.payload.model_copy(update={"screen": offline_screen(seq, seq, "shuttered")})
            event = event.model_copy(update={"seq": event.seq + 1, "payload": payload})
            pending = self.out_dir / ".window-shutter.pending"
            descriptor = os.open(pending, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(event.model_dump_json(by_alias=True).encode())
            pending.replace(public)

    def status(self) -> ConsentDocument | None:
        """Read the current owner-only consent document."""
        with self.locked():
            return self._read_unlocked()

    @contextmanager
    def locked(self) -> Generator[None, None, None]:
        """Hold the commit lock across capture validation and publication."""
        self._prepare_output()
        descriptor = os.open(self.lock_path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            deadline = time.monotonic() + self.lock_timeout_s
            while True:
                try:
                    fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        raise ConsentError("window consent lock acknowledgement timed out") from None
                    time.sleep(0.01)
            try:
                yield
            finally:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)

    def read_locked(self) -> ConsentDocument | None:
        """Read state while the caller already owns ``locked()``."""
        return self._read_unlocked()

    def _initial(self) -> ConsentDocument:
        return ConsentDocument(
            owner_uid=os.getuid(), boot_nonce=secrets.token_hex(24), generation=0, mode=ConsentMode.SHUTTERED
        )

    def _shuttered(self, current: ConsentDocument | None, boot_nonce: str) -> ConsentDocument:
        base = current or self._initial()
        return base.model_copy(
            update={"boot_nonce": boot_nonce, "generation": base.generation + 1, "mode": ConsentMode.SHUTTERED}
        )

    def _from_identity(self, base: ConsentDocument, identity: WindowIdentity, mode: ConsentMode) -> ConsentDocument:
        return base.model_copy(
            update={
                "owner_uid": os.getuid(),
                "generation": base.generation + 1,
                "mode": mode,
                "display": identity.display,
                "profile_generation": identity.profile_generation,
                "window_id": identity.window_id,
                "pid": identity.pid,
                "uid": identity.uid,
                "process_start_time": identity.process_start_time,
                "width": identity.width,
                "height": identity.height,
            }
        )

    def _prepare_output(self) -> None:
        self.out_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        metadata = self.out_dir.lstat()
        if not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid != os.getuid() or metadata.st_mode & 0o077:
            raise ConsentError("window consent output must be owner-only")

    def _read_unlocked(self) -> ConsentDocument | None:
        try:
            metadata = self.path.lstat()
            if (
                metadata.st_uid != os.getuid()
                or metadata.st_mode & 0o077
                or not self.path.is_file()
                or self.path.is_symlink()
            ):
                raise ConsentError("window consent document must be an owner-only regular file")
            document = ConsentDocument.model_validate_json(self.path.read_bytes())
        except FileNotFoundError:
            return None
        if document.owner_uid != os.getuid():
            raise ConsentError("window consent owner does not match")
        return document

    def _write_unlocked(self, document: ConsentDocument) -> ConsentDocument:
        pending = self.path.with_name(f".{self.path.name}.{os.getpid()}.pending")
        descriptor = os.open(pending, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(document.model_dump_json().encode())
        pending.replace(self.path)
        return document
