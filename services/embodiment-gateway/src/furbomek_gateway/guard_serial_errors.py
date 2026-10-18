"""Typed serial boundary errors shared by transport and I/O helpers."""

from enum import StrEnum
from typing import final, override


class GuardSerialErrorCode(StrEnum):
    """Stable serial boundary failures safe for MCP output."""

    CONNECTION = "connection"
    TIMEOUT = "timeout"
    WRITE = "write"
    PROTOCOL = "protocol"
    STALE_REPLY = "stale_reply"


@final
class GuardSerialError(Exception):
    """A typed serial transaction failure."""

    def __init__(self, code: GuardSerialErrorCode) -> None:
        """Create a non-sensitive serial failure."""
        super().__init__()
        self.code = code

    @override
    def __str__(self) -> str:
        return f"guard serial failed: {self.code.value}"
