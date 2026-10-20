"""Typed producer freshness checks for startup and health publication."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError

from .models import ActivityReadiness, Freshness, FreshnessHealth, TrackingReadiness


@dataclass(frozen=True, slots=True)
class ReadinessResult:
    """Result of validating both producer documents."""

    all_workers_alive: bool
    freshness: FreshnessHealth

    @property
    def ready(self) -> bool:
        """Return whether startup may proceed to OBS configuration."""
        return (
            self.all_workers_alive
            and self.freshness.tracking.fresh
            and self.freshness.activity.fresh
        )


def _age(now_s: float, produced_s: float) -> float:
    """Return a non-negative age, preserving future timestamps as invalid."""
    return now_s - produced_s if now_s >= produced_s else -1.0


def _tracking(path: Path, now_s: float) -> Freshness:
    """Validate the tracking document and evaluate its producer timestamp."""
    try:
        document = TrackingReadiness.model_validate_json(path.read_bytes())
    except (OSError, ValueError, ValidationError):
        return Freshness(age_s=None, fresh=False, schema_valid=False)
    age = _age(now_s, document.produced_unix_ms / 1000)
    return Freshness(
        age_s=age if age >= 0 else None,
        fresh=0 <= age <= document.ttl_ms / 1000,
        schema_valid=True,
    )


def _activity(path: Path, now_s: float) -> Freshness:
    """Validate the activity document and evaluate its producer timestamp."""
    try:
        document = ActivityReadiness.model_validate_json(path.read_bytes())
    except (OSError, ValueError, ValidationError):
        return Freshness(age_s=None, fresh=False, schema_valid=False)
    produced_s = document.observed_at.timestamp()
    age = _age(now_s, produced_s)
    return Freshness(
        age_s=age if age >= 0 else None,
        fresh=0 <= age <= document.ttl_ms / 1000,
        schema_valid=True,
    )


def check_readiness(
    kinect_dir: Path,
    now: Callable[[], float],
    all_workers_alive: bool,
) -> ReadinessResult:
    """Validate both JSON contracts using an injected wall clock."""
    now_s = now()
    freshness = FreshnessHealth(
        tracking=_tracking(kinect_dir / "tracking.json", now_s),
        activity=_activity(kinect_dir / "activity.json", now_s),
    )
    return ReadinessResult(all_workers_alive=all_workers_alive, freshness=freshness)


def iso_timestamp(value: datetime) -> str:
    """Serialize a UTC timestamp for fixture writers without local-time ambiguity."""
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
