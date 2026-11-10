# pyright: reportImportCycles=false
"""App-window candidate and screen-state lifecycle for the activity broker."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

import runtime as runtime_module
from screen import SCREEN_MAX_AGE_MS, CaptureError, DesktopHealth, ScreenPolicy
from window_consent import ConsentMode

if TYPE_CHECKING:
    from activity_broker import ActivityBroker
    from activity_models import ScreenState


def capture_app_window_candidate(broker: ActivityBroker, health: DesktopHealth, now_ms: int) -> None:
    """Capture and publish only while the locked explicit target remains stable."""
    store = broker.window_store
    capture = broker.window_capture
    if store is None or capture is None:
        return
    try:
        consent = store.read_locked()
        if consent is None or consent.mode is not ConsentMode.SHARED or consent.window_id is None:
            broker.frame = None
            runtime_module.invalidate_frames(broker.config.out_dir)
            return
        if broker.config.window_id is not None and broker.config.window_id != consent.window_id:
            broker.frame = None
            runtime_module.invalidate_frames(broker.config.out_dir)
            return
        target = runtime_module.select_window(broker.config.profile_home, consent.window_id)
        if not consent.matches(target):
            store.revoke_locked()
            broker.frame = None
            return
        if consent.generation != broker.frame_generation:
            capture.close()
        candidate = capture.capture(target)
        broker.last_capture_ms = now_ms
        broker.consume(broker.reader.poll(), now_ms)
        after_health = broker.health()
        current = runtime_module.select_window(broker.config.profile_home, target.window_id)
        valid = (
            after_health.alive
            and after_health.generation == health.generation
            and current == target
            and store.read_locked() == consent
        )
        if valid:
            broker.snapshot = replace(broker.snapshot, screen_seq=broker.snapshot.screen_seq + 1)
            broker.filename = runtime_module.write_frame(candidate, broker.config.out_dir, broker.snapshot.screen_seq)
            broker.frame = candidate
            broker.frame_generation = consent.generation
            return
    except (CaptureError, OSError, ValueError):
        store.revoke_locked()
    broker.frame = None
    runtime_module.invalidate_frames(broker.config.out_dir)


def app_window_ready(broker: ActivityBroker) -> bool:
    """Return whether explicit consent still names a target for this broker."""
    store = broker.window_store
    if store is None:
        return False
    consent = store.read_locked()
    allowed = (
        consent is not None
        and consent.mode is ConsentMode.SHARED
        and consent.window_id is not None
        and consent.boot_nonce == broker.window_nonce
        and consent.generation >= broker.window_generation
        and (broker.config.window_id is None or broker.config.window_id == consent.window_id)
    )
    if allowed and consent is not None:
        broker.window_generation = consent.generation
    return allowed


def screen_state(broker: ActivityBroker, now_ms: int, health: DesktopHealth) -> ScreenState:
    """Build the public screen state and delete pixels on every denial path."""
    if broker.config.screen_policy is ScreenPolicy.OFF:
        runtime_module.invalidate_frames(broker.config.out_dir)
        return runtime_module.offline_screen(broker.snapshot.screen_seq, broker.snapshot.screen_seq)
    if broker.config.screen_policy is ScreenPolicy.APP_WINDOW and not app_window_ready(broker):
        broker.frame = None
        runtime_module.invalidate_frames(broker.config.out_dir)
        return runtime_module.offline_screen(broker.snapshot.screen_seq, broker.snapshot.screen_seq, "shuttered")
    if broker.config.screen_policy is ScreenPolicy.APP_WINDOW and broker.frame_generation != broker.window_generation:
        broker.frame = None
    if not health.alive:
        broker.frame = None
        runtime_module.invalidate_frames(broker.config.out_dir)
        return runtime_module.offline_screen(broker.snapshot.screen_seq, broker.snapshot.screen_seq)
    if broker.snapshot.privacy.latched and broker.config.screen_policy is not ScreenPolicy.APP_WINDOW:
        broker.frame = None
        runtime_module.invalidate_frames(broker.config.out_dir)
        return runtime_module.offline_screen(broker.snapshot.screen_seq, broker.snapshot.screen_seq, "shuttered")
    if broker.frame is None or not 0 <= now_ms - broker.frame.captured_at_ms <= SCREEN_MAX_AGE_MS:
        broker.frame = None
        runtime_module.invalidate_frames(broker.config.out_dir)
        return runtime_module.offline_screen(broker.snapshot.screen_seq, broker.snapshot.screen_seq)
    return runtime_module.live_screen(broker.frame, broker.snapshot.screen_seq, broker.filename)
