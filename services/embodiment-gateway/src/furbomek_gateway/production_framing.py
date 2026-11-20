"""Trusted host observation clock to bounded renderer framing selection."""

from dataclasses import dataclass
from typing import Final, assert_never, final

from .framing_models import Fixed, Frame, FramingPreset, Manual, Subject
from .framing_policy import Decision, FramingPolicy
from .production_media_contracts import Framing
from .reaction_types import Clock

CLOCK_SKEW_MS: Final = 100


@dataclass(frozen=True, slots=True)
class FramingSelection:
    """Short-lived policy result; never accepted from a public/provider endpoint."""

    decision: Decision
    framing: Framing


@final
class ProductionFraming:
    """One owner-approved preset and authorized host-monotonic observation lane.

    The integration owner authenticates the producer before constructing Frame.
    Source strings alone do not authenticate; this object is never an HTTP DTO.
    """

    def __init__(self, preset: FramingPreset, clock: Clock) -> None:
        """Bind configuration and the same clock used by the scheduler."""
        self.policy = FramingPolicy(preset)
        self.clock = clock
        self.sources = {
            preset.tracking_source,
            *(r.trigger.source for r in preset.rules),
        }

    def step(self, frame: Frame) -> FramingSelection:
        """Reject wrong-clock or unconfigured-source data before policy changes."""
        if not 0 <= self.clock.monotonic_ms() - frame.now_ms <= CLOCK_SKEW_MS:
            msg = "observation clock is stale or future"
            raise ValueError(msg)
        if any(
            s.source not in self.sources or s.at_ms > frame.now_ms
            for s in frame.signals
        ):
            msg = "observation provenance rejected"
            raise ValueError(msg)
        decision = self.policy.step(frame)
        fallback = self.policy.preset.shot(self.policy.preset.fallback).target
        match fallback:
            case Fixed(roi=roi):
                fallback_roi = roi
            case Subject():
                msg = "validated preset requires fixed fallback"
                raise ValueError(msg)
            case _:
                assert_never(fallback)
        options = Framing(
            fallback_roi=fallback_roi,
            ttl_ms=self.policy.preset.lock_age_ms,
            transition=decision.transition,
        )
        if decision.hold_previous:
            return FramingSelection(
                decision, options.model_copy(update={"rules": ("hold",)})
            )
        match decision.target.target:
            case Fixed(roi=roi):
                options = options.model_copy(update={"roi": roi})
            case Subject(id=identity):
                options = options.model_copy(
                    update={"subject_id": identity, "rules": ("subject", "hold")}
                )
            case _:
                assert_never(decision.target.target)
        return FramingSelection(decision, options)

    def override(self, command: Manual) -> None:
        """Owner-only bounded hold/override; next step still needs a fresh clock."""
        self.policy.override(command)
