"""Versioned framing presets and adapter inputs; never action authority."""

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from .effect_contracts import Contract, Identifier

Millis = Annotated[int, Field(ge=0, le=600000)]
Timestamp = Annotated[int, Field(ge=0)]
Unit = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]


class Roi(Contract):
    """Normalized camera coordinates, independent of stage geometry."""

    x: Unit
    y: Unit
    width: Annotated[float, Field(gt=0, le=1, allow_inf_nan=False)]
    height: Annotated[float, Field(gt=0, le=1, allow_inf_nan=False)]

    @model_validator(mode="after")
    def contained(self) -> Self:
        """Reject rectangles outside the camera frame."""
        if self.x + self.width > 1 or self.y + self.height > 1:
            msg = "ROI exceeds camera frame"
            raise ValueError(msg)
        return self


class Subject(Contract):
    """Owner-approved tracked person or object identity."""

    kind: Literal["person", "object"]
    id: Identifier


class Fixed(Contract):
    """Owner-approved fixed normalized shot."""

    kind: Literal["fixed"]
    roi: Roi


Target = Annotated[Subject | Fixed, Field(discriminator="kind")]


class Shot(Contract):
    """Stable preset-local shot reference."""

    id: Identifier
    target: Target


class Trigger(Contract):
    """Closed predicate on an authenticated adapter's typed signal."""

    kind: Literal["observation", "event"]
    source: Identifier
    subject: Subject
    event: Literal["attention", "activity", "reaction"] = "attention"
    confidence: Unit = 0.8
    max_age_ms: Annotated[int, Field(ge=1, le=10000)] = 1000


class Rule(Contract):
    """Continuous qualification followed by bounded release hysteresis."""

    id: Identifier
    target: Identifier
    trigger: Trigger
    priority: Annotated[int, Field(ge=1, le=100)]
    dwell_ms: Millis = 500
    release_ms: Millis = 1000


class Transition(Contract):
    """Renderer must enforce these limits; policy emits intent only."""

    duration_ms: Annotated[int, Field(ge=100, le=10000)] = 500
    pan_units_per_second: Annotated[float, Field(gt=0, le=1)] = 0.25
    zoom: Annotated[float, Field(ge=1, le=4)] = 1.0
    zoom_per_second: Annotated[float, Field(gt=0, le=1)] = 0.5


class FramingPreset(Contract):
    """Persist only this validated configuration, never timers or authority."""

    schema_version: Literal["furbomek.framing.v1"] = "furbomek.framing.v1"
    id: Identifier
    shots: Annotated[tuple[Shot, ...], Field(min_length=1, max_length=32)]
    default: Identifier
    fallback: Identifier
    rules: Annotated[tuple[Rule, ...], Field(max_length=32)] = ()
    transition: Transition = Transition()
    hold_ms: Millis = 1000
    lock_age_ms: Annotated[int, Field(ge=1, le=600)] = 300
    output_ttl_ms: Annotated[int, Field(ge=1, le=600)] = 300
    lock_confidence: Unit = 0.8
    tracking_source: Identifier
    sample_gap_ms: Annotated[int, Field(ge=1, le=10000)] = 1000
    minimum_shot_ms: Annotated[int, Field(ge=100, le=600000)] = 1000
    ttl_ms: Annotated[int, Field(ge=1, le=600000)] = 30000

    @model_validator(mode="after")
    def references(self) -> Self:
        """Resolve all references and require a stable terminal fallback."""
        shots = {shot.id: shot for shot in self.shots}
        if len(shots) != len(self.shots) or len({r.id for r in self.rules}) != len(
            self.rules
        ):
            msg = "duplicate framing identity"
            raise ValueError(msg)
        if self.default not in shots or self.fallback not in shots:
            msg = "unknown framing target"
            raise ValueError(msg)
        if shots[self.fallback].target.kind != "fixed":
            msg = "fallback must be a stable fixed shot"
            raise ValueError(msg)
        subjects = tuple(s.target for s in self.shots if s.target.kind != "fixed")
        if any(
            r.target not in shots or r.trigger.subject not in subjects
            for r in self.rules
        ):
            msg = "unapproved rule target or trigger subject"
            raise ValueError(msg)
        return self

    def shot(self, identity: str) -> Shot:
        """Resolve a previously validated reference."""
        return next(shot for shot in self.shots if shot.id == identity)


class Signal(Contract):
    """Host-monotonic sample from an authenticated adapter, never raw chat.

    The caller binds source out of band. A matching source string is not proof
    of authentication. Task14 must not expose this model as a public input API.
    """

    kind: Literal["observation", "event"]
    source: Identifier
    subject: Subject
    at_ms: Timestamp
    confidence: Unit
    event: Literal["attention", "activity", "reaction"] = "attention"


class Frame(Contract):
    """One complete adapter snapshot on the engine's monotonic clock."""

    now_ms: Timestamp
    signals: Annotated[tuple[Signal, ...], Field(max_length=128)] = ()


class Manual(Contract):
    """Owner-authorized override, always bounded by preset TTL."""

    target: Identifier
    duration_ms: Annotated[int, Field(ge=1, le=600000)]
