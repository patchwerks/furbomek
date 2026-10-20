"""Persist residual ownership so a failed cleanup cannot admit a second session."""

from __future__ import annotations

import os
import stat
from collections.abc import Mapping
from pathlib import Path
from typing import Annotated, ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .processes import ManagedProcess, group_alive


class OwnershipError(Exception):
    """Refuse ambiguous ownership without signalling persisted process IDs."""

    reason: str

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


class OwnerFence(BaseModel):
    """Private ledger; a pending spawn cannot be cleared by guessing its outcome."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid", strict=True)
    schema_version: Literal[1] = 1
    pending_spawn: bool = False
    pgids: tuple[Annotated[int, Field(gt=0)], ...] = ()


def assert_available(path: Path) -> None:
    """Check the fence while the caller holds the session flock."""
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or metadata.st_mode & 0o077
    ):
        raise OwnershipError("media ownership record is not an owned private file")
    try:
        if metadata.st_size > 4096:
            raise OwnershipError("media ownership record is oversized")
        fence = OwnerFence.model_validate_json(path.read_bytes())
    except ValidationError as error:
        raise OwnershipError("media ownership record is invalid") from error
    if fence.pending_spawn:
        raise OwnershipError("ambiguous media spawn requires operator reconciliation")
    if any(group_alive(pgid) for pgid in fence.pgids):
        raise OwnershipError("previous media workers still own the session")


def record_owners(
    path: Path, children: Mapping[str, ManagedProcess], *, pending_spawn: bool = False
) -> None:
    """Fence before spawning; clear only after every known group is gone."""
    groups = tuple(sorted({child.pgid for child in children.values() if group_alive(child.pgid)}))
    if not groups and not pending_spawn:
        path.unlink(missing_ok=True)
        return
    fence = OwnerFence(pending_spawn=pending_spawn, pgids=groups)
    pending = path.with_name("host-session.owners.next.json")
    _ = pending.write_text(fence.model_dump_json(), encoding="utf-8")
    _ = pending.chmod(0o600)
    _ = pending.replace(path)
