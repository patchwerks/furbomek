"""Private consumer wire values; no provider or public input API."""

from typing import Annotated, Literal

from pydantic import Field

from .effect_contracts import Contract, GraphicsEffect, Identifier, SfxEffect
from .framing_models import Roi, Transition

Revision = Annotated[int, Field(ge=0, le=2147483646)]
Look = Literal["rgb.fixed.v1", "rgb.crimson.v1", "xyz.depth.v1", "xyz.crimson.v1"]


class Framing(Contract):
    """Normalized trusted decision with renderer-enforced motion bounds."""

    subject_id: Identifier = "object-furbomek"
    rules: tuple[Literal["subject", "fixed", "hold"], ...] = ("fixed",)
    ttl_ms: Annotated[int, Field(ge=1, le=600)] = 300
    roi: Roi = Roi(x=0.0, y=0.0, width=1.0, height=1.0)
    transition: Transition | None = None
    valid_until_ms: Annotated[int, Field(ge=0)] = 0
    fallback_roi: Roi = Roi(x=0.0, y=0.0, width=1.0, height=1.0)


class VisualSettings(Contract):
    """Public-safe controls; authority and observations never travel here."""

    look: Look = "rgb.fixed.v1"
    point_pixels: Annotated[float, Field(ge=0.75, le=3.6, allow_inf_nan=False)] = 1.45
    zoom: Annotated[float, Field(ge=0.7, le=1.5, allow_inf_nan=False)] = 1.0
    yaw: Annotated[float, Field(ge=-0.55, le=0.55, allow_inf_nan=False)] = 0.0
    pitch: Annotated[float, Field(ge=-0.32, le=0.32, allow_inf_nan=False)] = 0.0
    hud_visible: bool = True
    insets_visible: bool = True
    pulse_hz: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)] = 0.0
    intensity_percent: Annotated[int, Field(ge=0, le=100)] = 0


class RenderRequest(VisualSettings):
    """Exact revision/owner CAS including local actor and consumer epoch."""

    schema_version: Literal["furbomek.effects.v1"] = "furbomek.effects.v1"
    consumer_id: Identifier
    actor_id: Identifier = "legacy"
    cue_id: Identifier
    owner: Identifier
    expected_owner: str = ""
    expected_revision: Revision
    revision: Annotated[int, Field(ge=1, le=2147483647)]
    issued_ms: int
    duration_ms: Annotated[int, Field(ge=1, le=30000)]
    operation: Literal["apply", "release", "stop"] = "apply"
    framing: Framing = Framing()
    preset: Literal["neutral", "rgb", "xyz", "liquidation"] = "neutral"


class RenderReceipt(Contract):
    """Heartbeat and exact admitted bytes from the real Godot consumer."""

    schema_version: Literal["furbomek.effects-ack.v1"]
    consumer_id: Identifier
    actor_id: str
    status: str
    revision: Revision
    owner: str
    cue_id: str
    look: Look
    source_available: bool
    source_sequence: int
    framing: str
    matched_id: str
    depth_provenance: Literal[
        "native_measured_xyz_512x424", "optical_rgb_no_extra_depth"
    ]
    published_ms: int
    effective: RenderRequest | None


class SfxRequest(Contract):
    """Locally enabled candidate path; submitting it is not playback proof."""

    schema_version: Literal["furbomek.sfx.v1"] = "furbomek.sfx.v1"
    consumer_id: Identifier
    actor_id: Identifier
    cue_id: Identifier
    owner: Identifier
    expected_owner: Identifier
    expected_revision: Revision
    revision: Annotated[int, Field(ge=1, le=2147483647)]
    issued_ms: int
    duration_ms: Annotated[int, Field(ge=1, le=30000)]
    preset: Literal["liquidation", "acknowledge"]
    gain_percent: Annotated[int, Field(ge=0, le=100)]
    operation: Literal["apply", "stop"] = "apply"


class SfxReceipt(Contract):
    """OBS state observation, distinct from captured-audio qualification."""

    schema_version: Literal["furbomek.sfx-ack.v1"]
    consumer_id: Identifier
    actor_id: str
    status: str
    owner: str
    cue_id: str
    revision: Revision
    muted: bool
    source_available: bool
    published_ms: int
    preset: Literal["liquidation", "acknowledge"]
    gain_percent: Annotated[int, Field(ge=0, le=100)]
    duration_ms: Annotated[int, Field(ge=1, le=30000)]


def graphics_effect(receipt: RenderReceipt) -> GraphicsEffect | None:
    """Project only an exact supported applied renderer request."""
    request = receipt.effective
    if request is None:
        return None
    return GraphicsEffect(
        capability="graphics.pulse.v1",
        preset=request.preset,
        intensity_percent=request.intensity_percent,
        duration_ms=request.duration_ms,
    )


def sfx_effect(receipt: SfxReceipt) -> SfxEffect | None:
    """Only observed playing has an active effect value."""
    if receipt.status != "playing":
        return None
    return SfxEffect(
        capability="sfx.preset.v1",
        preset=receipt.preset,
        gain_percent=receipt.gain_percent,
        duration_ms=receipt.duration_ms,
    )
