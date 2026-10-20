"""Fail-closed privacy reduction for tool-call lifecycle events."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hermes_feed import SpoolEvent


@dataclass(frozen=True, slots=True)
class HoldKey:
    """Identity of one tool call hold."""

    session: str
    call: str


@dataclass(frozen=True, slots=True)
class PrivacyState:
    """Fail-closed latch and concurrent tool-call holds."""

    latched: bool
    uncertain: bool
    release_requested: bool
    generation_required: bool
    fresh_generation: bool
    fresh_capture_required: bool
    generation: str | None
    holds: frozenset[HoldKey]

    @classmethod
    def initial(cls, checkpoint_valid: bool) -> PrivacyState:
        """Start shuttered when no durable checkpoint proves continuity."""
        return cls(
            latched=not checkpoint_valid,
            uncertain=not checkpoint_valid,
            release_requested=False,
            generation_required=not checkpoint_valid,
            fresh_generation=False,
            fresh_capture_required=True,
            generation=None,
            holds=frozenset(),
        )


_SENSITIVE_ACTIONS = frozenset({"typing", "using password vault", "opening"})


def is_sensitive(event: SpoolEvent) -> bool:
    """Return whether an event can expose private desktop pixels."""
    return event.shutter or (
        event.action in _SENSITIVE_ACTIONS
        and (
            event.category == "COMPUTER"
            or event.action == "using password vault"
            or event.detail in {"private page", "local page"}
        )
    )


def mark_uncertain(state: PrivacyState) -> PrivacyState:
    """Latch privacy after a malformed, unreadable, or discontinuous spool."""
    return replace(
        state, latched=True, uncertain=True, release_requested=False, generation_required=True, fresh_generation=False
    )


def observe_generation(state: PrivacyState, generation: str | None) -> PrivacyState:
    """Record a dedicated desktop generation without treating it as pixels."""
    if generation is None:
        return state
    if generation == state.generation:
        return state
    return replace(
        state,
        generation=generation,
        latched=True,
        uncertain=state.uncertain,
        generation_required=True,
        fresh_generation=True,
        release_requested=state.release_requested,
    )


def apply_privacy_event(state: PrivacyState, event: SpoolEvent) -> PrivacyState:
    """Apply exactly one tool lifecycle event to holds and the privacy latch."""
    if event.kind != "tool":
        return state
    key = HoldKey(event.session, event.call)
    sensitive = is_sensitive(event)
    if event.phase == "running":
        if not event.session or not event.call:
            return replace(state, latched=True, uncertain=True, release_requested=False, generation_required=True)
        holds = state.holds | {key}
        return replace(
            state,
            holds=holds,
            latched=state.latched or sensitive,
            release_requested=False if sensitive else state.release_requested,
        )
    if event.phase in ("ok", "error"):
        if not event.session or not event.call or key not in state.holds:
            return replace(state, latched=True, uncertain=True, release_requested=False, generation_required=True)
        holds = state.holds - {key}
        release = state.release_requested
        if event.privacy_release and event.phase == "ok" and not sensitive:
            release = True
        return replace(state, holds=holds, latched=state.latched or sensitive, release_requested=release)
    return state


def candidate_allowed(state: PrivacyState) -> bool:
    """Allow an in-memory frame candidate when it can be proven safe."""
    if not state.latched:
        return True
    return state.release_requested and not state.holds and (not state.generation_required or state.fresh_generation)


def complete_candidate(state: PrivacyState, generation: str | None, valid: bool) -> PrivacyState:
    """Commit a fresh candidate only after the post-capture spool check."""
    if not valid or generation is None or generation != state.generation:
        return state
    if state.latched:
        if not candidate_allowed(state):
            return state
        return replace(
            state,
            latched=False,
            uncertain=False,
            release_requested=False,
            generation_required=False,
            fresh_capture_required=False,
        )
    return replace(state, fresh_capture_required=False)
