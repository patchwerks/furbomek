"""Exclusive bounded owner-only mailbox, anchored to an open directory."""

import fcntl
import os
import stat
from contextlib import ExitStack, suppress
from pathlib import Path
from types import TracebackType
from typing import Final, Literal, Self, final
from uuid import uuid4

from .reaction_types import StorePrivacyError

DIRECTORY_MODE: Final = 0o700
FILE_MODE: Final = 0o600
MAX_BYTES: Final = 8192

MailboxName = Literal["effects.json", "effects-ack.json", "sfx.json", "sfx-ack.json"]


@final
class PrivateMailbox:
    """One writer per private directory; caller owns this context's lifetime."""

    def __init__(self, directory: Path) -> None:
        """Reject symlinks, repository paths, shared modes and competing writers."""
        self.directory = directory.absolute()
        self._stack = ExitStack()
        if any((p / ".git").exists() for p in self.directory.resolve().parents):
            raise StorePrivacyError(str(directory))
        try:
            self._fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            _ = self._stack.callback(os.close, self._fd)
            self._check_directory()
            lock = os.open(
                "production-media.lock",
                os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW,
                0o600,
                dir_fd=self._fd,
            )
            _ = self._stack.callback(os.close, lock)
            self._check(lock)
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (OSError, StorePrivacyError):
            self._stack.close()
            raise

    def _check_directory(self) -> None:
        info = os.fstat(self._fd)
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != DIRECTORY_MODE:
            raise StorePrivacyError(str(self.directory))

    def _check(self, descriptor: int) -> None:
        info = os.fstat(descriptor)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or info.st_nlink != 1
            or stat.S_IMODE(info.st_mode) != FILE_MODE
        ):
            raise StorePrivacyError(str(self.directory))

    def read(self, name: MailboxName) -> bytes:
        """Reject oversized, replaced or non-private receipt files."""
        flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
        with os.fdopen(os.open(name, flags, dir_fd=self._fd), "rb") as source:
            self._check(source.fileno())
            data = source.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise StorePrivacyError(str(self.directory))
        return data

    def write(self, name: MailboxName, data: str) -> None:
        """Atomic fixed-path publication; never follow an existing target."""
        if len(data.encode()) > MAX_BYTES:
            raise StorePrivacyError(str(self.directory))
        stage = f".production-media-{uuid4().hex}"
        try:
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
            with os.fdopen(os.open(stage, flags, 0o600, dir_fd=self._fd), "w") as file:
                _ = file.write(data)
                file.flush()
                os.fsync(file.fileno())
            os.rename(stage, name, src_dir_fd=self._fd, dst_dir_fd=self._fd)
        finally:
            with suppress(FileNotFoundError):
                os.unlink(stage, dir_fd=self._fd)

    def __enter__(self) -> Self:
        """Keep the exclusive writer until context exit."""
        return self

    def __exit__(
        self,
        _kind: type[BaseException] | None,
        _value: BaseException | None,
        _traceback: TracebackType | None,
    ) -> None:
        """Release only owned descriptors; persisted requests retain their TTL."""
        self._stack.close()
