"""Immutable offline evidence contracts; parsing is owned by parsing.py."""

from dataclasses import dataclass
from enum import Enum
from typing import NewType

Nanoseconds = NewType("Nanoseconds", int)


class Fault(str, Enum):
    OBS = "obs_stall"
    STAGE = "stage_missing"
    STALE = "tracking_stale"
    BUMP = "tracking_bump"
    DISCONNECT = "tracking_disconnect"
    RF = "rf_loss"
    MAC = "mac_loss"
    TUNNEL = "tunnel_loss"
    BRODEX = "brodex_restart"
    RESET = "reset"
    BROWNOUT = "brownout"
    BOUNDARY = "near_boundary"
    CANCEL = "cancel"
    STOP = "stop"
    EFFECT = "effect_stall"
    OVERRIDE = "owner_override"
    PROVIDER = "provider_outage"
    RECONNECT = "provider_reconnect"
    BACKLOG = "event_backlog"
    BATTERY = "battery_service"
    CUTOFF = "independent_cutoff"
    RESOURCE = "resource_contention"
    EARLY = "early_loss"


class Action(str, Enum):
    QUALIFY = "qualify"
    TRIGGER = "trigger"
    DISPATCH = "dispatch"
    LOSS = "loss"
    RECOVER = "recover"


class EvidenceKind(str, Enum):
    AUTH = "authenticated_link"
    CUTOFF = "independent_cutoff"
    STAGE = "stage"
    CONTAINMENT = "containment"
    LIVE = "matched_live_scope"
    SOAK = "private_24h_soak"
    AUTHORIZATION = "operator_authorization"


@dataclass(frozen=True, slots=True)
class Frame:
    at_ns: Nanoseconds
    rendered: int
    lagged: int


@dataclass(frozen=True, slots=True)
class Latency:
    received_ns: Nanoseconds
    completed_ns: Nanoseconds
    idle: bool


@dataclass(frozen=True, slots=True)
class Timings:
    clock: str
    width: int
    height: int
    fps: int
    frames: tuple[Frame, ...]
    cues: tuple[Latency, ...]
    motion: tuple[Latency, ...]
    provider: tuple[Latency, ...]
    camera: tuple[Latency, ...]
    encoder: tuple[Latency, ...]


@dataclass(frozen=True, slots=True)
class Event:
    at_ns: Nanoseconds
    action: Action


@dataclass(frozen=True, slots=True)
class FaultCase:
    fault: Fault
    events: tuple[Event, ...]


@dataclass(frozen=True, slots=True)
class Scope:
    source_revision: str
    robot_image_sha256: str
    bridge_image_sha256: str
    profile_sha256: str
    stage_sha256: str
    calibration_sha256: str
    motion_envelope_sha256: str
    session: str


@dataclass(frozen=True, slots=True)
class Evidence:
    kind: EvidenceKind
    scope: Scope
    captured_unix_ms: int
    expires_unix_ms: int
    payload: str
    payload_sha256: str


@dataclass(frozen=True, slots=True)
class Manifest:
    schema_version: int
    scope: Scope
    timings: Timings
    faults: tuple[FaultCase, ...]
    evidence: tuple[Evidence, ...]
