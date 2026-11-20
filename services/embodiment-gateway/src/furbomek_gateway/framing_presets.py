"""Bounded preset serialization and a stdin/stdout-only JSON rehearsal."""

import json
import sys
from typing import Annotated, Final, Self

from pydantic import Field, model_validator

from .effect_contracts import Contract
from .framing_models import Frame, FramingPreset
from .framing_policy import Decision, FramingPolicy
from .reaction_contracts import unique_keys

MAX_STORE_BYTES: Final = 262144
MAX_REHEARSAL_BYTES: Final = 1048576


class Presets(Contract):
    """Owner-store payload; activation is a separate caller operation."""

    presets: Annotated[tuple[FramingPreset, ...], Field(max_length=32)]

    @model_validator(mode="after")
    def unique_ids(self) -> Self:
        """Reject ambiguous owner-store activation references."""
        if len({p.id for p in self.presets}) != len(self.presets):
            msg = "duplicate preset identity"
            raise ValueError(msg)
        return self

    def save(self) -> bytes:
        """Return validated bytes; caller owns atomic storage and permissions."""
        raw = self.model_dump_json().encode()
        if len(raw) > MAX_STORE_BYTES:
            msg = "preset storage exceeds size limit"
            raise ValueError(msg)
        return raw

    @classmethod
    def load(cls, raw: bytes) -> "Presets":
        """Restore configuration only, rejecting ambiguous JSON fields."""
        if len(raw) > MAX_STORE_BYTES:
            msg = "preset storage exceeds size limit"
            raise ValueError(msg)
        json.loads(raw, object_pairs_hook=unique_keys)
        return cls.model_validate_json(raw)


class Rehearsal(Contract):
    """Dry adapter snapshots, never a production admission endpoint."""

    preset: FramingPreset
    frames: Annotated[tuple[Frame, ...], Field(min_length=1, max_length=1000)]


class RehearsalResult(Contract):
    """Reason-coded dry decisions, with no applied-state claim."""

    decisions: tuple[Decision, ...]


def main() -> None:
    """Read bounded JSON on stdin and emit decisions without device/file I/O."""
    raw = sys.stdin.buffer.read(MAX_REHEARSAL_BYTES + 1)
    if len(raw) > MAX_REHEARSAL_BYTES:
        msg = "rehearsal exceeds size limit"
        raise ValueError(msg)
    json.loads(raw, object_pairs_hook=unique_keys)
    request = Rehearsal.model_validate_json(raw)
    policy = FramingPolicy(request.preset)
    result = RehearsalResult(decisions=tuple(policy.step(f) for f in request.frames))
    _ = sys.stdout.write(result.model_dump_json() + "\n")


if __name__ == "__main__":
    main()
