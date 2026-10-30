"""Ordered local character inputs and bounded, durable presentation state."""

from __future__ import annotations

from typing import ClassVar, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

CharacterPhase = Literal["idle", "thinking", "speaking", "interrupted", "error"]
IDENTIFIER = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$"
MAX_RETIRED = 128


class CharacterInput(BaseModel):
    """Strict input; local file ownership supplies authorization, never this payload."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid", strict=True)

    schema_version: Literal["furbomek.character-input.v1"]
    session: str = Field(pattern=IDENTIFIER)
    seq: int = Field(ge=0, le=9_007_199_254_740_991)
    observed_ms: int = Field(gt=0)
    ttl_ms: int = Field(gt=0, le=30_000)
    phase: CharacterPhase
    utterance: str | None = Field(default=None, pattern=IDENTIFIER)
    cancel_of: str | None = Field(default=None, pattern=IDENTIFIER)

    @model_validator(mode="after")
    def check_identity(self) -> Self:
        """Require one utterance for speech and one cancellation target for interruption."""
        if (self.phase == "speaking") != (self.utterance is not None):
            msg = "only speaking requires an utterance"
            raise ValueError(msg)
        if (self.phase == "interrupted") != (self.cancel_of is not None):
            msg = "only interrupted requires a cancellation target"
            raise ValueError(msg)
        return self


class CharacterState(BaseModel):
    """Existing broker checkpoint member; contains no speech, tools or external authority."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    session: str = Field(pattern=IDENTIFIER)
    seq: int = Field(default=-1, ge=-1, le=9_007_199_254_740_991)
    observed_ms: int = Field(default=0, ge=0)
    expires_ms: int = Field(default=0, ge=0)
    phase: CharacterPhase = "idle"
    utterance: str | None = Field(default=None, pattern=IDENTIFIER)
    retired: tuple[str, ...] = Field(default=(), max_length=MAX_RETIRED)
    exhausted: bool = False


def retire(state: CharacterState, *identities: str | None) -> CharacterState:
    """Never evict cancellation evidence to make room for new speech."""
    retired = tuple(dict.fromkeys((*state.retired, *(value for value in identities if value is not None))))
    if len(retired) > MAX_RETIRED:
        return state.model_copy(update={"phase": "error", "utterance": None, "exhausted": True})
    return state.model_copy(update={"retired": retired})


def expire(state: CharacterState, now_ms: int, *, uncertain: bool = False) -> CharacterState:
    """Clear transients on expiry, clock reversal or lost input continuity."""
    if state.exhausted:
        return state
    if uncertain:
        return retire(state, state.utterance).model_copy(
            update={"phase": "error", "utterance": None, "exhausted": True}
        )
    if now_ms < state.observed_ms or now_ms >= state.expires_ms:
        retired = retire(state, state.utterance)
        if retired.exhausted:
            return retired
        return retired.model_copy(update={"phase": "idle", "utterance": None})
    return state


def apply_character(state: CharacterState, event: CharacterInput, now_ms: int) -> CharacterState:
    """Apply fresh ordered input without accepting replay or reviving retired speech."""
    if state.exhausted or event.session != state.session or event.observed_ms > now_ms:
        return state
    if event.phase == "interrupted":
        return _apply_cancellation(state, event, now_ms)
    if (
        event.seq <= state.seq
        or event.observed_ms < state.observed_ms
        or not event.observed_ms <= now_ms < event.observed_ms + event.ttl_ms
        or event.utterance in state.retired
    ):
        return state
    current = expire(state, now_ms)
    if event.utterance in current.retired or current.exhausted:
        return current
    previous = current.utterance if current.utterance != event.utterance else None
    updated = retire(current, previous, event.cancel_of)
    if updated.exhausted:
        return updated
    return updated.model_copy(
        update={
            "seq": event.seq,
            "observed_ms": event.observed_ms,
            "expires_ms": event.observed_ms + event.ttl_ms,
            "phase": event.phase,
            "utterance": event.utterance,
        }
    )


def _apply_cancellation(state: CharacterState, event: CharacterInput, now_ms: int) -> CharacterState:
    """Revocation survives presentation TTL and delivery order without reviving stale visuals."""
    if event.cancel_of in state.retired and event.seq <= state.seq:
        return state
    current = expire(state, now_ms)
    updated = retire(current, event.cancel_of)
    if updated.exhausted:
        return updated
    updated = updated.model_copy(update={"seq": max(updated.seq, event.seq)})
    if current.utterance not in (None, event.cancel_of):
        return updated
    fresh = event.observed_ms <= now_ms < event.observed_ms + event.ttl_ms
    newer = event.seq > state.seq and event.observed_ms >= state.observed_ms
    if current.utterance == event.cancel_of or (fresh and newer):
        return updated.model_copy(
            update={
                "phase": "interrupted" if fresh and newer else "idle",
                "utterance": None,
                "observed_ms": max(state.observed_ms, event.observed_ms),
                "expires_ms": event.observed_ms + event.ttl_ms if fresh and newer else now_ms,
            }
        )
    return updated
