"""Durable activity broker runtime loop."""

from __future__ import annotations

import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Final, Protocol

from activity_models import BrokerState, ScreenState
from cursor import CursorSnapshot, IncrementalSpoolReader, PollResult
from persistence import RuntimeSnapshot, load_checkpoint, published_sequences, restore_snapshot, save_checkpoint
from privacy import (
    PrivacyState,
    apply_privacy_event,
    candidate_allowed,
    complete_candidate,
    mark_uncertain,
    observe_generation,
)
from publisher import publish
from reducer import apply_event, idle_state, refresh_timeline
from screen import (
    SCREEN_MAX_AGE_MS,
    SCREEN_RING,
    CapturedFrame,
    CaptureError,
    DesktopHealth,
    ScreenPolicy,
    capture_frame,
    desktop_health,
    invalidate_frames,
    live_screen,
    offline_screen,
    write_frame,
)

HEARTBEAT_MS: Final = 1_000
ACTIVE_FRAME_MS: Final = 250
IDLE_FRAME_MS: Final = 1_000


class Clock(Protocol):
    """Clock seam for deterministic polling tests."""

    def now_ms(self) -> int:
        """Return current Unix milliseconds."""
        ...

    def sleep(self, seconds: float) -> None:
        """Sleep between polling cycles."""
        ...


class SystemClock:
    """Wall-clock implementation used by the CLI."""

    def now_ms(self) -> int:
        """Return current Unix milliseconds."""
        return int(time.time() * 1000)

    def sleep(self, seconds: float) -> None:
        """Sleep between polling cycles."""
        time.sleep(seconds)


@dataclass(frozen=True, slots=True)
class RunConfig:
    """Paths and policy for one broker process."""

    spool: Path
    profile_home: Path
    out_dir: Path
    once: bool = False
    screen_policy: ScreenPolicy = ScreenPolicy.OFF


class ActivityBroker:
    """Own incremental consumption, privacy state, and publication cadence."""

    config: RunConfig
    clock: Clock
    snapshot: RuntimeSnapshot
    reader: IncrementalSpoolReader
    checkpoint_path: Path
    frame: CapturedFrame | None
    filename: str
    last_capture_ms: int
    last_publish_ms: int
    last_screen: ScreenState | None

    def __init__(self, config: RunConfig, clock: Clock | None = None) -> None:
        """Restore durable state and prepare one broker run."""
        self.config = config
        self.clock = clock or SystemClock()
        self.config.out_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        checkpoint_path = self.config.out_dir / "activity.state.json"
        checkpoint = load_checkpoint(checkpoint_path)
        output_publication, output_screen = published_sequences(self.config.out_dir)
        if checkpoint is None:
            now_ms = self.clock.now_ms()
            self.snapshot = RuntimeSnapshot(
                CursorSnapshot(None, 0),
                BrokerState.initial(now_ms),
                PrivacyState.initial(checkpoint_valid=False),
                output_publication,
                output_screen,
            )
        else:
            restored = restore_snapshot(checkpoint)
            self.snapshot = replace(
                restored,
                publication_seq=max(restored.publication_seq, output_publication),
                screen_seq=max(restored.screen_seq, output_screen),
            )
        self.reader = IncrementalSpoolReader(self.config.spool, self.snapshot.cursor)
        self.checkpoint_path = checkpoint_path
        self.frame = None
        self.filename = f"hermes-screen-{self.snapshot.screen_seq % SCREEN_RING}.jpg"
        self.last_capture_ms = 0
        self.last_publish_ms = 0
        self.last_screen = None
        if self.config.screen_policy is ScreenPolicy.OFF:
            invalidate_frames(self.config.out_dir)

    def run(self) -> None:
        """Run the bounded poll/publish loop."""
        try:
            while True:
                now_ms = self.clock.now_ms()
                self.step(now_ms)
                if self.config.once:
                    return
                self.clock.sleep(0.12)
        finally:
            self.reader.close()

    def step(self, now_ms: int) -> None:
        """Poll, reduce, capture, and publish one deterministic cycle."""
        self._consume(self.reader.poll(), now_ms)
        self.snapshot = replace(self.snapshot, broker=idle_state(self.snapshot.broker, now_ms))
        health = self._health()
        self.snapshot = replace(
            self.snapshot,
            privacy=observe_generation(self.snapshot.privacy, health.generation if health.alive else None),
        )
        if self._capture_due(now_ms, health):
            self._capture_candidate(health, now_ms)
        screen = self._screen(now_ms, health)
        self.snapshot = replace(self.snapshot, broker=refresh_timeline(self.snapshot.broker, now_ms))
        if self.config.once or self.last_screen != screen or now_ms - self.last_publish_ms >= HEARTBEAT_MS:
            next_seq = self.snapshot.publication_seq + 1
            broker = replace(self.snapshot.broker, seq=next_seq, shutter=self.snapshot.privacy.latched)
            self.snapshot = replace(self.snapshot, broker=broker, publication_seq=next_seq)
            publish(broker, now_ms, screen, self.config.out_dir)
            self.last_publish_ms = now_ms
            self.last_screen = screen
        save_checkpoint(self.checkpoint_path, self.snapshot)

    def _consume(self, result: PollResult, now_ms: int) -> None:
        privacy = self.snapshot.privacy
        if not result.readable or result.gap or result.uncertain:
            privacy = mark_uncertain(privacy)
        broker = self.snapshot.broker
        for event in result.events:
            broker = apply_event(broker, event, now_ms)
            privacy = apply_privacy_event(privacy, event)
        self.snapshot = replace(self.snapshot, broker=broker, privacy=privacy, cursor=result.cursor)

    def _health(self) -> DesktopHealth:
        if self.config.screen_policy is ScreenPolicy.OFF:
            return DesktopHealth(alive=False, env={}, generation=None)
        return desktop_health(self.config.profile_home)

    def _capture_due(self, now_ms: int, health: DesktopHealth) -> bool:
        if (
            self.config.screen_policy is ScreenPolicy.OFF
            or not health.alive
            or not candidate_allowed(self.snapshot.privacy)
        ):
            return False
        interval = ACTIVE_FRAME_MS if self.snapshot.broker.phase != "idle" else IDLE_FRAME_MS
        return now_ms - self.last_capture_ms >= interval

    def _capture_candidate(self, health: DesktopHealth, now_ms: int) -> None:
        try:
            candidate = capture_frame(health.env)
        except (CaptureError, OSError):
            self.frame = None
            invalidate_frames(self.config.out_dir)
            return
        after_capture = self.reader.poll()
        self._consume(after_capture, now_ms)
        after_health = self._health()
        privacy = observe_generation(self.snapshot.privacy, after_health.generation if after_health.alive else None)
        valid = (
            after_capture.readable
            and not after_capture.gap
            and not after_capture.uncertain
            and after_health.alive
            and after_health.generation == health.generation
        )
        privacy = complete_candidate(privacy, after_health.generation, valid)
        self.snapshot = replace(self.snapshot, privacy=privacy)
        self.last_capture_ms = now_ms
        if valid and not privacy.latched and not privacy.holds:
            self.snapshot = replace(self.snapshot, screen_seq=self.snapshot.screen_seq + 1)
            self.filename = write_frame(candidate, self.config.out_dir, self.snapshot.screen_seq)
            self.frame = candidate
            return
        self.frame = None
        invalidate_frames(self.config.out_dir)

    def _screen(self, now_ms: int, health: DesktopHealth) -> ScreenState:
        if self.config.screen_policy is ScreenPolicy.OFF:
            invalidate_frames(self.config.out_dir)
            return offline_screen(self.snapshot.screen_seq, self.snapshot.screen_seq)
        if not health.alive:
            self.frame = None
            invalidate_frames(self.config.out_dir)
            return offline_screen(self.snapshot.screen_seq, self.snapshot.screen_seq)
        if self.snapshot.privacy.latched:
            self.frame = None
            invalidate_frames(self.config.out_dir)
            return offline_screen(self.snapshot.screen_seq, self.snapshot.screen_seq, "shuttered")
        if (
            self.frame is None
            or now_ms - self.frame.captured_at_ms < 0
            or now_ms - self.frame.captured_at_ms > SCREEN_MAX_AGE_MS
        ):
            self.frame = None
            invalidate_frames(self.config.out_dir)
            return offline_screen(self.snapshot.screen_seq, self.snapshot.screen_seq)
        return live_screen(self.frame, self.snapshot.screen_seq, self.filename)


def run(config: RunConfig, clock: Clock | None = None) -> None:
    """Run one configured activity broker."""
    ActivityBroker(config, clock).run()
