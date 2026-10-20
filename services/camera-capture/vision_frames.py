from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Literal

import cv2
import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, ConfigDict, Field

FrameName = Annotated[str, Field(pattern=r"^frame-[0-3]\.(bin|jpg\.bin|optical\.bin|map\.bin)$")]
TargetKind = Literal["body", "face", "surface", "object"]


class CameraMeta(BaseModel):
    model_config = ConfigDict(frozen=True)
    sequence: int = Field(ge=1)
    capture_monotonic_ns: int = Field(ge=0)
    frame_file: FrameName
    image_file: FrameName
    optical_file: FrameName
    map_file: FrameName
    width: Literal[512]
    height: Literal[424]
    valid_points: int = Field(ge=0, le=217088)
    capture_fps: float = Field(ge=0)


class Track(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str = "pending"
    kind: TargetKind
    label: str
    box: tuple[float, float, float, float]
    optical_box: tuple[float, float, float, float] | None
    world_box: tuple[float, float, float, float, float, float]
    world_outline: tuple[tuple[float, float, float], ...] = ()
    probe_world: tuple[float, float, float]
    probe_pixel: tuple[float, float]
    probe_optical: tuple[float, float] | None = None
    score: float = Field(ge=0, le=1)
    score_type: str
    landmarks: tuple[tuple[float, float], ...] = ()


class VisionFrame(BaseModel):
    model_config = ConfigDict(frozen=True, serialize_by_alias=True)
    schema_version: Literal["furbomek.vision.v1"] = Field(default="furbomek.vision.v1", serialization_alias="schema")
    sequence: int
    capture_monotonic_ns: int
    produced_monotonic_ns: int
    produced_unix_ms: int
    frame_file: FrameName
    image_file: FrameName
    optical_file: FrameName
    valid_points: int
    capture_fps: float
    ttl_ms: Literal[600] = 600
    tracks: tuple[Track, ...]


@dataclass(frozen=True, slots=True)
class Snapshot:
    meta: CameraMeta
    points: NDArray[np.float32]
    image: NDArray[np.uint8]
    color_map: NDArray[np.int32]


def load_snapshot(directory: Path) -> Snapshot | None:
    meta = CameraMeta.model_validate_json((directory / "metadata.json").read_bytes())
    cloud = (directory / meta.frame_file).read_bytes()
    picture = (directory / meta.image_file).read_bytes()
    mapping = (directory / meta.map_file).read_bytes()
    if len(cloud) != 16 + 217088 * 64 or len(picture) < 5 or len(mapping) != 4 + 217088 * 4:
        return None
    magic, version, sequence, count = struct.unpack_from("<4I", cloud)
    if (magic, version, sequence, count) != (0x32434B46, 1, meta.sequence, 217088):
        return None
    if struct.unpack_from("<I", picture)[0] != sequence or struct.unpack_from("<I", mapping)[0] != sequence:
        return None
    image = cv2.imdecode(np.frombuffer(picture, dtype=np.uint8, offset=4), cv2.IMREAD_COLOR)
    if image is None or image.shape != (424, 512, 3):
        return None
    return Snapshot(meta, np.frombuffer(cloud, dtype="<f4", offset=16).reshape(424, 512, 16),
                    image, np.frombuffer(mapping, dtype="<i4", offset=4).reshape(424, 512))


def frame_sequence_matches(path: Path, sequence: int) -> bool:
    """Reject a ring slot replaced or removed while detection was running."""
    try:
        with path.open("rb") as stream:
            header = stream.read(16)
    except FileNotFoundError:
        return False
    return len(header) == 16 and struct.unpack("<4I", header)[2] == sequence
