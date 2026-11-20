"""Strict, bounded standard-library parser for untrusted offline JSON only."""

import hashlib
import json
import os
import re
import stat
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Final, TypeAlias, TypeVar

from models import (
    Action,
    Event,
    Evidence,
    EvidenceKind,
    Fault,
    FaultCase,
    Frame,
    Latency,
    Manifest,
    Nanoseconds,
    Scope,
    Timings,
)

Json: TypeAlias = None | bool | int | float | str | list["Json"] | dict[str, "Json"]
MAX_BYTES: Final = 4_000_000
T = TypeVar("T")
E = TypeVar("E", bound=Enum)


@dataclass(frozen=True, slots=True)
class InputError(Exception):
    code: str

    def __str__(self) -> str:
        return self.code


@dataclass(frozen=True, slots=True)
class Record:
    values: dict[str, Json]

    def __getitem__(self, key: str) -> Json:
        return self.values[key]


def record(value: Json, keys: str) -> Record:
    if not isinstance(value, dict) or set(value) != set(keys.split()):
        raise InputError("invalid_fields")
    return Record(value)


def integer(value: Json) -> int:
    if type(value) is not int or not 0 <= value <= 10**18:
        raise InputError("invalid_nonnegative_integer")
    return value


def text(value: Json) -> str:
    if not isinstance(value, str) or not 1 <= len(value) <= 65536:
        raise InputError("invalid_text")
    return value


def token(value: Json) -> str:
    result = text(value)
    if re.fullmatch(r"[A-Za-z0-9_-]{1,80}", result) is None:
        raise InputError("invalid_identifier")
    return result


def digest(value: Json, length: int = 64) -> str:
    result = text(value)
    if re.fullmatch(r"[0-9a-f]{" + str(length) + "}", result) is None:
        raise InputError("invalid_digest")
    return result


def boolean(value: Json) -> bool:
    if type(value) is not bool:
        raise InputError("invalid_boolean")
    return value


def sequence(value: Json, parser: Callable[[Json], T]) -> tuple[T, ...]:
    if not isinstance(value, list) or len(value) > 100000:
        raise InputError("invalid_sequence")
    return tuple(parser(item) for item in value)


def variant(value: Json, kind: type[E]) -> E:
    try:
        return kind(text(value))
    except ValueError as error:
        raise InputError("invalid_variant") from error


def frame(value: Json) -> Frame:
    data = record(value, "at_ns rendered lagged")
    return Frame(
        Nanoseconds(integer(data["at_ns"])),
        integer(data["rendered"]),
        integer(data["lagged"]),
    )


def latency(value: Json) -> Latency:
    data = record(value, "received_ns completed_ns idle")
    return Latency(
        Nanoseconds(integer(data["received_ns"])),
        Nanoseconds(integer(data["completed_ns"])),
        boolean(data["idle"]),
    )


def timings(value: Json) -> Timings:
    data = record(
        value, "clock width height fps frames cues motion provider camera encoder"
    )
    return Timings(
        token(data["clock"]),
        integer(data["width"]),
        integer(data["height"]),
        integer(data["fps"]),
        sequence(data["frames"], frame),
        sequence(data["cues"], latency),
        sequence(data["motion"], latency),
        sequence(data["provider"], latency),
        sequence(data["camera"], latency),
        sequence(data["encoder"], latency),
    )


def event(value: Json) -> Event:
    data = record(value, "at_ns action")
    return Event(Nanoseconds(integer(data["at_ns"])), variant(data["action"], Action))


def fault_case(value: Json) -> FaultCase:
    data = record(value, "fault events")
    return FaultCase(variant(data["fault"], Fault), sequence(data["events"], event))


def scope(value: Json) -> Scope:
    data = record(
        value,
        "source_revision robot_image_sha256 bridge_image_sha256 profile_sha256 stage_sha256 calibration_sha256 motion_envelope_sha256 session",
    )
    return Scope(
        digest(data["source_revision"], 40),
        digest(data["robot_image_sha256"]),
        digest(data["bridge_image_sha256"]),
        digest(data["profile_sha256"]),
        digest(data["stage_sha256"]),
        digest(data["calibration_sha256"]),
        digest(data["motion_envelope_sha256"]),
        token(data["session"]),
    )


def evidence(value: Json) -> Evidence:
    data = record(
        value, "kind scope captured_unix_ms expires_unix_ms payload payload_sha256"
    )
    return Evidence(
        variant(data["kind"], EvidenceKind),
        scope(data["scope"]),
        integer(data["captured_unix_ms"]),
        integer(data["expires_unix_ms"]),
        text(data["payload"]),
        digest(data["payload_sha256"]),
    )


def manifest(value: Json) -> Manifest:
    data = record(value, "schema_version scope timings faults evidence")
    if integer(data["schema_version"]) != 1:
        raise InputError("unsupported_schema_version")
    return Manifest(
        1,
        scope(data["scope"]),
        timings(data["timings"]),
        sequence(data["faults"], fault_case),
        sequence(data["evidence"], evidence),
    )


def unique_pairs(pairs: list[tuple[str, Json]]) -> dict[str, Json]:
    # JSON boundary scratch map: duplicate authority keys must never be overwritten.
    result: dict[str, Json] = {}
    for key, value in pairs:
        if key in result:
            raise InputError("duplicate_key")
        result[key] = value
    return result


def reject_constant(value: str) -> Json:
    raise InputError("nonfinite_number")


@dataclass(frozen=True, slots=True)
class LoadedManifest:
    data: Manifest
    sha256: str


def load(path: Path) -> LoadedManifest:
    # Reject special files before opening: even opening a device can have effects.
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_BYTES:
        raise InputError("not_bounded_regular_file")
    # Recheck the descriptor to detect replacement; never follow a final symlink.
    descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    with os.fdopen(descriptor, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_BYTES:
            raise InputError("not_bounded_regular_file")
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise InputError("input_too_large")
    try:
        data = manifest(
            json.loads(
                raw, object_pairs_hook=unique_pairs, parse_constant=reject_constant
            )
        )
        return LoadedManifest(data, hashlib.sha256(raw).hexdigest())
    except (ValueError, UnicodeDecodeError, RecursionError) as error:
        raise InputError("invalid_json") from error
