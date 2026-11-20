"""Closed, versioned production effects; descriptions never grant authority."""

from typing import Annotated, ClassVar, Final, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

Identifier = Annotated[str, Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}$")]
Duration = Annotated[int, Field(ge=1, le=30000)]
Percent = Annotated[int, Field(ge=0, le=100)]
CapabilityId = Literal[
    "hud.redacted.v1",
    "graphics.pulse.v1",
    "sfx.preset.v1",
    "motion.qualified.v1",
    "voice.reserved.v1",
    "face.reserved.v1",
]
Resource = Literal["hud", "graphics", "sfx", "robot", "voice", "face"]


class Contract(BaseModel):
    """Immutable strict boundary shared by production DTOs."""

    model_config: ClassVar[ConfigDict] = ConfigDict(
        extra="forbid", strict=True, frozen=True
    )


class HudEffect(Contract):
    """Only locally curated redacted text templates are projectable."""

    capability: Literal["hud.redacted.v1"]
    template: Literal["liquidation", "neutral"]
    duration_ms: Duration


class GraphicsEffect(Contract):
    """Reviewed renderer presets; no renderer commands or asset paths."""

    capability: Literal["graphics.pulse.v1"]
    preset: Literal["liquidation", "neutral", "rgb", "xyz"]
    intensity_percent: Percent
    duration_ms: Duration


class SfxEffect(Contract):
    """A local sound catalog reference, never a file or URL."""

    capability: Literal["sfx.preset.v1"]
    preset: Literal["liquidation", "acknowledge"]
    gain_percent: Percent
    duration_ms: Duration


class MotionEffect(Contract):
    """Optional intent requiring separate motion admission and qualification."""

    capability: Literal["motion.qualified.v1"]
    action: Literal[
        "active",
        "sleep",
        "forward",
        "backward",
        "left",
        "right",
        "turn_left",
        "turn_right",
    ]
    duration_ms: Annotated[int, Field(ge=1, le=1000)]
    qualification: Literal["operator_present_supported_bench"]


class VoiceEffect(Contract):
    """Reserved jabberwerk adapter contract; unavailable in this version."""

    capability: Literal["voice.reserved.v1"]
    preset: Literal["reserved"]
    duration_ms: Duration


class FaceEffect(Contract):
    """Reserved face contract; unavailable in this version."""

    capability: Literal["face.reserved.v1"]
    preset: Literal["reserved"]
    duration_ms: Duration


Effect = Annotated[
    HudEffect | GraphicsEffect | SfxEffect | MotionEffect | VoiceEffect | FaceEffect,
    Field(discriminator="capability"),
]


class CapabilityDefinition(Contract):
    """Registry metadata fixed by reviewed code, never by a provider."""

    capability: CapabilityId
    resource: Resource
    required_state: Literal[
        "renderer_ready", "audio_ready", "qualified_bench", "unavailable"
    ]
    available: bool
    physical: bool
    max_duration_ms: Duration


CAPABILITIES: Final = (
    CapabilityDefinition(
        capability="hud.redacted.v1",
        resource="hud",
        required_state="renderer_ready",
        available=True,
        physical=False,
        max_duration_ms=30000,
    ),
    CapabilityDefinition(
        capability="graphics.pulse.v1",
        resource="graphics",
        required_state="renderer_ready",
        available=True,
        physical=False,
        max_duration_ms=30000,
    ),
    CapabilityDefinition(
        capability="sfx.preset.v1",
        resource="sfx",
        required_state="audio_ready",
        available=True,
        physical=False,
        max_duration_ms=30000,
    ),
    CapabilityDefinition(
        capability="motion.qualified.v1",
        resource="robot",
        required_state="qualified_bench",
        available=False,
        physical=True,
        max_duration_ms=1000,
    ),
    CapabilityDefinition(
        capability="voice.reserved.v1",
        resource="voice",
        required_state="unavailable",
        available=False,
        physical=False,
        max_duration_ms=30000,
    ),
    CapabilityDefinition(
        capability="face.reserved.v1",
        resource="face",
        required_state="unavailable",
        available=False,
        physical=True,
        max_duration_ms=30000,
    ),
)


def capability_definition(capability: CapabilityId) -> CapabilityDefinition:
    """Resolve a closed versioned reference against the reviewed registry."""
    return next(item for item in CAPABILITIES if item.capability == capability)


class AppliedAck(Contract):
    """Property ownership receipt, not proof of physical motion or perception."""

    schema_version: Literal[1] = 1
    status: Literal["applied"]
    cue_id: Identifier
    capability: CapabilityId
    resource: Resource
    owner: Identifier
    previous_revision: Annotated[int, Field(ge=0)]
    revision: Annotated[int, Field(ge=1)]
    effective: Effect
    available: Literal[True]

    @model_validator(mode="after")
    def valid_ownership(self) -> Self:
        """Reject inconsistent receipts and reserved-capability success claims."""
        definition = capability_definition(self.capability)
        if (
            self.effective.capability != self.capability
            or self.resource != definition.resource
            or self.revision <= self.previous_revision
            or definition.required_state == "unavailable"
        ):
            msg = "inconsistent applied ownership receipt"
            raise ValueError(msg)
        return self
