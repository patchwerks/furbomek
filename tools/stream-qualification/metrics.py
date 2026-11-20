"""Calculate observed counter deltas and nearest-rank p95 from monotonic samples."""

from dataclasses import dataclass
from math import ceil

from models import Latency, Timings


@dataclass(frozen=True, slots=True)
class Distribution:
    count: int
    p95_ms: float | None


@dataclass(frozen=True, slots=True)
class Metrics:
    duration_seconds: float
    rendered_frames: int
    lagged_frames: int
    lag_percent: float | None
    cue: Distribution
    idle_dispatch: Distribution
    nonidle_motion_count: int
    provider: Distribution
    camera: Distribution
    encoder: Distribution
    holds: tuple[str, ...]


def distribution(samples: tuple[Latency, ...]) -> Distribution:
    values = sorted(
        (sample.completed_ns - sample.received_ns) / 1_000_000 for sample in samples
    )
    return Distribution(
        len(values), values[ceil(len(values) * 0.95) - 1] if values else None
    )


def evaluate(data: Timings) -> Metrics:
    holds: list[str] = []
    duration, rendered, lagged = 0.0, 0, 0
    if (data.width, data.height, data.fps) != (1920, 1080, 30):
        holds.append("representative_1080p30_required")
    if len(data.frames) < 2:
        holds.append("missing_timed_frames")
    else:
        if any(frame.lagged > frame.rendered for frame in data.frames):
            holds.append("invalid_frame_counters")
        first, last = data.frames[0], data.frames[-1]
        duration = (last.at_ns - first.at_ns) / 1_000_000_000
        rendered = last.rendered - first.rendered
        lagged = last.lagged - first.lagged
        for previous, current in zip(data.frames, data.frames[1:]):
            span = (current.at_ns - previous.at_ns) / 1_000_000_000
            frame_delta = current.rendered - previous.rendered
            lag_delta = current.lagged - previous.lagged
            if (
                not 0 < span <= 60
                or frame_delta <= 0
                or not 0 <= lag_delta <= frame_delta
            ):
                holds.append("frame_counter_gap_or_reset")
            if abs(frame_delta - span * 30) > 2:
                holds.append("frame_rate_mismatch")
        if duration < 1800:
            holds.append("representative_duration_below_30_minutes")
    lag_percent = lagged * 100 / rendered if rendered > 0 else None
    if lag_percent is None or not 0 <= lag_percent <= 2:
        holds.append("obs_render_lag_target_missed")
    groups = {
        "cue": data.cues,
        "motion": data.motion,
        "provider": data.provider,
        "camera": data.camera,
        "encoder": data.encoder,
    }
    for name, samples in groups.items():
        if not samples:
            holds.append(f"missing_{name}_timed_samples")
        previous_received = -1
        for sample in samples:
            if (
                sample.completed_ns < sample.received_ns
                or sample.received_ns <= previous_received
            ):
                holds.append(f"invalid_{name}_monotonic_samples")
            if (
                data.frames
                and not data.frames[0].at_ns
                <= sample.received_ns
                <= sample.completed_ns
                <= data.frames[-1].at_ns
            ):
                holds.append(f"{name}_outside_frame_window")
            previous_received = sample.received_ns
    cue = distribution(data.cues)
    idle = distribution(tuple(sample for sample in data.motion if sample.idle))
    if cue.p95_ms is None or cue.p95_ms > 250:
        holds.append("local_cue_p95_target_missed")
    if idle.p95_ms is None or idle.p95_ms > 500:
        holds.append("idle_dispatch_p95_target_missed")
    return Metrics(
        duration,
        rendered,
        lagged,
        lag_percent,
        cue,
        idle,
        sum(not sample.idle for sample in data.motion),
        distribution(data.provider),
        distribution(data.camera),
        distribution(data.encoder),
        tuple(sorted(set(holds))),
    )
