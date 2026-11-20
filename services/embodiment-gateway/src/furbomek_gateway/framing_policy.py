"""Pure deterministic framing policy; no camera, renderer, filesystem or motion I/O."""

from dataclasses import dataclass
from typing import Literal, final

from .effect_contracts import Contract
from .framing_models import Frame, FramingPreset, Manual, Rule, Shot, Transition

Reason = Literal[
    "default",
    "qualified",
    "release_hold",
    "minimum_hold",
    "loss_hold",
    "fallback",
    "manual",
    "expired",
    "reset",
]


class Decision(Contract):
    """Immutable intention; downstream application needs a revision ACK."""

    preset: str
    target: Shot
    reason: Reason
    rule: str | None
    hold_previous: bool
    transition: Transition
    expires_ms: int


@dataclass(frozen=True, slots=True)
class Qualification:
    """Continuity measured only across fresh complete snapshots."""

    rule: str
    since: int
    seen: int


@final
class FramingPolicy:
    """Own transient timers for one validated preset and monotonic epoch.

    Rebinding a camera, source authorization or preset requires a new instance.
    Restores load configuration only; pending/manual state never survives restart.
    Each step consumes a complete snapshot, including absence. Host adapters must
    authenticate sources and map timestamps to this epoch before calling step.
    """

    def __init__(self, preset: FramingPreset) -> None:
        """Start an inactive lease using validated owner configuration."""
        self._preset = preset
        self._now = -1
        self._started: int | None = None
        self._active: Rule | None = None
        self._selected_at = 0
        self._qualifications: dict[str, Qualification] = {}
        self._last_seen = 0
        self._locked_at: int | None = None
        self._locked_target: str | None = None
        self._manual: tuple[str, int] | None = None

    @property
    def preset(self) -> FramingPreset:
        """Expose immutable configuration; rebind by creating a new engine."""
        return self._preset

    def override(self, command: Manual) -> None:
        """Select an approved shot at the last tick; no implicit clock reads."""
        if self._now < 0 or command.target not in {s.id for s in self.preset.shots}:
            msg = "override requires a tick and an approved target"
            raise ValueError(msg)
        self._manual = (
            command.target,
            self._now + min(command.duration_ms, self.preset.ttl_ms),
        )
        self._qualifications.clear()
        self._active = None

    def reset(self, frame: Frame) -> Decision:
        """Owner reset clears transient state without renewing the preset lease."""
        self._check_time(frame)
        self._manual = None
        self._active = None
        self._qualifications.clear()
        self._locked_at = None
        self._locked_target = None
        if self._expired(frame.now_ms):
            return self._decision(self.preset.fallback, "expired", frame)
        return self._decision(self.preset.default, "reset", frame)

    def _expired(self, now_ms: int) -> bool:
        return (
            self._started is not None and now_ms >= self._started + self.preset.ttl_ms
        )

    def _check_time(self, frame: Frame) -> None:
        if frame.now_ms < self._now:
            msg = "monotonic clock moved backwards"
            raise ValueError(msg)
        self._now = frame.now_ms
        if self._started is None:
            self._started = frame.now_ms

    def _matches(self, rule: Rule, frame: Frame) -> bool:
        trigger = rule.trigger
        limits = {"observation": self.preset.lock_age_ms, "event": trigger.max_age_ms}
        age_limit = min(trigger.max_age_ms, limits[trigger.kind])
        return any(
            s.kind == trigger.kind
            and s.source == trigger.source
            and s.subject == trigger.subject
            and s.event == trigger.event
            and s.confidence >= trigger.confidence
            and 0 <= frame.now_ms - s.at_ms <= age_limit
            for s in frame.signals
        )

    def _qualify(self, frame: Frame) -> list[Rule]:
        ready: list[Rule] = []
        for rule in self.preset.rules:
            if not self._matches(rule, frame):
                _ = self._qualifications.pop(rule.id, None)
                continue
            previous = self._qualifications.get(rule.id)
            since = frame.now_ms
            if (
                previous is not None
                and frame.now_ms - previous.seen <= self.preset.sample_gap_ms
            ):
                since = previous.since
            self._qualifications[rule.id] = Qualification(rule.id, since, frame.now_ms)
            if frame.now_ms - since >= rule.dwell_ms:
                ready.append(rule)
        return sorted(ready, key=lambda rule: (-rule.priority, rule.id))

    def step(self, frame: Frame) -> Decision:
        """Resolve priority, continuity, release and bounded loss fallback."""
        self._check_time(frame)
        if self._expired(frame.now_ms):
            self._manual = None
            self._active = None
            return self._decision(self.preset.fallback, "expired", frame)
        if self._manual is not None:
            target, until = self._manual
            if frame.now_ms < until:
                return self._decision(target, "manual", frame)
            self._manual = None
            self._qualifications.clear()
        ready = self._qualify(frame)
        active = self._active
        if active is not None and self._matches(active, frame):
            self._last_seen = frame.now_ms
        candidate = ready[0] if ready else None
        if active is not None:
            held = frame.now_ms - self._selected_at < self.preset.minimum_shot_ms
            releasing = frame.now_ms - self._last_seen < active.release_ms
            retain = candidate is None or candidate.priority <= active.priority or held
            if (held or releasing or self._matches(active, frame)) and retain:
                reason: Reason = "minimum_hold" if held else "release_hold"
                if self._matches(active, frame):
                    reason = "qualified"
                return self._decision(active.target, reason, frame)
        if candidate is not None:
            self._active = candidate
            self._selected_at = frame.now_ms
            self._last_seen = frame.now_ms
            return self._decision(candidate.target, "qualified", frame)
        self._active = None
        return self._decision(self.preset.default, "default", frame)

    def _decision(self, identity: str, reason: Reason, frame: Frame) -> Decision:
        shot = self.preset.shot(identity)
        holding = False
        if shot.target.kind != "fixed":
            locked = any(
                s.kind == "observation"
                and s.subject == shot.target
                and s.source == self.preset.tracking_source
                and s.confidence >= self.preset.lock_confidence
                and 0 <= frame.now_ms - s.at_ms <= self.preset.lock_age_ms
                for s in frame.signals
            )
            if locked:
                self._locked_at, self._locked_target = frame.now_ms, identity
            elif (
                self._locked_target == identity
                and self._locked_at is not None
                and frame.now_ms - self._locked_at < self.preset.hold_ms
            ):
                holding, reason = True, "loss_hold"
            else:
                shot, reason = self.preset.shot(self.preset.fallback), "fallback"
        if shot.target.kind == "fixed":
            self._locked_target = None
            self._locked_at = None
        return Decision(
            preset=self.preset.id,
            target=shot,
            reason=reason,
            rule=self._active.id if self._active else None,
            hold_previous=holding,
            transition=self.preset.transition,
            expires_ms=frame.now_ms + self.preset.output_ttl_ms,
        )
