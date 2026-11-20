"""Private event admission and bounded portable reaction graphs."""

import json
from typing import Annotated, Final, Literal, Self

from pydantic import Field, JsonValue, model_validator

from .effect_contracts import (
    Contract,
    Duration,
    Effect,
    Identifier,
    capability_definition,
)

MAX_HORIZON_MS: Final = 30000
MAX_PACK_BYTES: Final = 65536


class PrivateEvent(Contract):
    """Trusted-adapter envelope; identity is private and never renderer output."""

    schema_version: Literal[1] = 1
    source: Identifier
    scope: Identifier
    stable_id: Identifier
    causation_id: Identifier
    origin: Literal["adapter"]
    route: Literal["curated_preset"] = "curated_preset"
    occurred_ms: Annotated[int, Field(ge=0)]
    received_ms: Annotated[int, Field(ge=0)]
    max_age_ms: Annotated[int, Field(ge=1, le=10000)] = 10000
    replay_window_ms: Annotated[int, Field(ge=10000, le=86400000)] = 60000

    @model_validator(mode="after")
    def valid_receipt(self) -> Self:
        """Reject unverifiable/future/stale provider age before admission."""
        self.require_fresh(self.received_ms)
        return self

    def require_fresh(self, now_ms: int) -> None:
        """Recheck age at dispatch with a trusted host timestamp."""
        if not self.received_ms <= now_ms <= self.occurred_ms + self.max_age_ms:
            msg = "event freshness rejected"
            raise ValueError(msg)
        if self.occurred_ms > self.received_ms:
            msg = "event freshness rejected"
            raise ValueError(msg)

    @property
    def dedupe_key(self) -> tuple[str, str, str]:
        """Persist atomically across restart; pack choice cannot change identity."""
        return self.source, self.scope, self.stable_id

    @property
    def retain_until_ms(self) -> int:
        """Minimum retention deadline for the future durable runtime store."""
        return self.received_ms + self.replay_window_ms


class Cue(Contract):
    """Dependencies mean completion; independent nodes may execute in parallel."""

    id: Identifier
    after: Annotated[tuple[Identifier, ...], Field(max_length=16)]
    effect: Effect
    condition: Literal["always", "capability_available", "motion_qualified"]
    ttl_ms: Duration
    on_unavailable: Literal["skip", "cancel_pack"]
    on_fault: Literal["cancel_pack"]

    @model_validator(mode="after")
    def valid_cue(self) -> Self:
        """Enforce local cue budgets and qualification conditions."""
        if len(set(self.after)) != len(self.after):
            msg = "duplicate dependency identity"
            raise ValueError(msg)
        if self.effect.duration_ms > self.ttl_ms:
            msg = "cue exceeds TTL"
            raise ValueError(msg)
        definition = capability_definition(self.effect.capability)
        if definition.physical and self.condition != "motion_qualified":
            msg = "physical cue requires qualification condition"
            raise ValueError(msg)
        return self


class ReactionPack(Contract):
    """Finite, fail-closed cue DAG; no loops, scripts or authority claims."""

    schema_version: Literal[1]
    effects_version: Literal[1]
    pack_id: Identifier
    pack_version: Literal["1.0.0"]
    priority: Literal["curated"]
    cancellation: Literal["cancel_pending_stop_active"]
    cues: Annotated[tuple[Cue, ...], Field(min_length=1, max_length=16)]

    @property
    def horizon_ms(self) -> int:
        """Maximum completion time with dependencies and parallel branches."""
        ends: dict[str, int] = {}
        pending = list(self.cues)
        while pending:
            ready = [cue for cue in pending if set(cue.after) <= ends.keys()]
            if not ready:
                msg = "cycle in cue graph"
                raise ValueError(msg)
            for cue in ready:
                ends[cue.id] = (
                    max((ends[key] for key in cue.after), default=0)
                    + cue.effect.duration_ms
                )
                pending.remove(cue)
        return max(ends.values())

    @model_validator(mode="after")
    def valid_graph(self) -> Self:
        """Reject unsafe graphs before any downstream adapter is consulted."""
        ids = {cue.id for cue in self.cues}
        if len(ids) != len(self.cues):
            msg = "duplicate cue identity"
            raise ValueError(msg)
        ancestors: dict[str, set[str]] = {}
        pending = list(self.cues)
        for cue in pending:
            if not set(cue.after) <= ids:
                msg = "unknown dependency"
                raise ValueError(msg)
        while pending:
            ready = [cue for cue in pending if set(cue.after) <= ancestors.keys()]
            if not ready:
                msg = "cycle in cue graph"
                raise ValueError(msg)
            for cue in ready:
                ancestors[cue.id] = set(cue.after).union(
                    *(ancestors[key] for key in cue.after)
                )
                pending.remove(cue)
        for index, cue in enumerate(self.cues):
            left = capability_definition(cue.effect.capability)
            for other in self.cues[index + 1 :]:
                right = capability_definition(other.effect.capability)
                ordered = cue.id in ancestors[other.id] or other.id in ancestors[cue.id]
                if not ordered and (
                    left.resource == right.resource
                    or (left.physical and right.physical)
                ):
                    msg = "concurrent resource or physical cue conflict"
                    raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def valid_horizon(self) -> Self:
        """Reject a schedule outside the initial session budget."""
        if self.horizon_ms > MAX_HORIZON_MS:
            msg = "schedule exceeds 30000 ms horizon"
            raise ValueError(msg)
        return self


def unique_keys(pairs: list[tuple[str, JsonValue]]) -> dict[str, JsonValue]:
    """JSON decoder hook rejects duplicate fields before DTO parsing."""
    result: dict[str, JsonValue] = {}
    for key, value in pairs:
        if key in result:
            msg = "duplicate JSON key"
            raise ValueError(msg)
        result[key] = value
    return result


def parse_pack(raw: bytes) -> ReactionPack:
    """Parse bounded UTF-8 JSON, then enforce structural and semantic contracts."""
    if len(raw) > MAX_PACK_BYTES:
        msg = "pack exceeds 65536 bytes"
        raise ValueError(msg)
    json.loads(raw.decode("utf-8"), object_pairs_hook=unique_keys)
    return ReactionPack.model_validate_json(raw)
