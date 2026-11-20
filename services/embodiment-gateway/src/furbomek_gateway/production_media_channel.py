"""Real private graphics/SFX ReactionAdapter; submission never implies application."""

from dataclasses import dataclass
from typing import Final, assert_never
from uuid import uuid4

from pydantic import ValidationError

from .effect_contracts import Resource
from .production_mailbox import PrivateMailbox
from .production_media_contracts import (
    RenderReceipt,
    RenderRequest,
    SfxReceipt,
    VisualSettings,
    graphics_effect,
    sfx_effect,
)
from .reaction_types import (
    AdapterFaultError,
    Clock,
    PropertyState,
    StorePrivacyError,
)

GRAPHICS: Final = "graphics"
SFX: Final = "sfx"
RENDER_FRESH_MS: Final = 600
AUDIO_FRESH_MS: Final = 1500
HISTORY_LIMIT: Final = 64


@dataclass(frozen=True, slots=True)
class MediaBinding:
    """Operator-local identity and explicit candidate audio opt-in."""

    actor_id: str
    sfx_enabled: bool = False


class MediaChannel:
    """Bound consumer epochs and actual property observations for one writer."""

    def __init__(
        self, mailbox: PrivateMailbox, clock: Clock, binding: MediaBinding
    ) -> None:
        """Keep bounded observed history for exact restoration."""
        self.mailbox: PrivateMailbox = mailbox
        self.clock: Clock = clock
        self.binding: MediaBinding = binding
        self.observed: dict[int, RenderRequest | None] = {}
        self.epochs: dict[str, str] = {}
        self.visual_pending: dict[str, RenderRequest] = {}

    def renderer(self) -> RenderReceipt:
        """Read a fresh receipt pinned to this process epoch."""
        receipt = RenderReceipt.model_validate_json(
            self.mailbox.read("effects-ack.json")
        )
        if not 0 <= self.clock.epoch_ms() - receipt.published_ms <= RENDER_FRESH_MS:
            raise AdapterFaultError(GRAPHICS)
        expected = (
            "optical_rgb_no_extra_depth"
            if receipt.look.startswith("rgb")
            else "native_measured_xyz_512x424"
        )
        if receipt.depth_provenance != expected:
            raise AdapterFaultError(GRAPHICS)
        previous = self.epochs.setdefault("graphics", receipt.consumer_id)
        if previous != receipt.consumer_id:
            raise AdapterFaultError(GRAPHICS)
        return receipt

    def audio(self) -> SfxReceipt:
        """Read candidate OBS observation without asserting audio qualification."""
        receipt = SfxReceipt.model_validate_json(self.mailbox.read("sfx-ack.json"))
        if not 0 <= self.clock.epoch_ms() - receipt.published_ms <= AUDIO_FRESH_MS:
            raise AdapterFaultError(SFX)
        previous = self.epochs.setdefault("sfx", receipt.consumer_id)
        if previous != receipt.consumer_id:
            raise AdapterFaultError(SFX)
        return receipt

    def available(self, resource: Resource) -> bool:
        """Require fresh consumer observations; unsupported resources remain HOLD."""
        try:
            match resource:
                case "graphics":
                    receipt = self.renderer()
                    return receipt.source_available and receipt.owner != "operator"
                case "sfx":
                    receipt = self.audio()
                    return (
                        self.binding.sfx_enabled
                        and receipt.source_available
                        and not receipt.muted
                    )
                case "hud" | "robot" | "voice" | "face":
                    return False
                case _:
                    assert_never(resource)
        except (OSError, ValidationError, StorePrivacyError, AdapterFaultError):
            return False

    def snapshot(self, resource: Resource) -> PropertyState:
        """Read actual state, including same-value manual revision changes."""
        match resource:
            case "graphics":
                receipt = self.renderer()
                self.observed[receipt.revision] = receipt.effective
                if len(self.observed) > HISTORY_LIMIT:
                    del self.observed[next(iter(self.observed))]
                return PropertyState(
                    resource=resource,
                    revision=receipt.revision,
                    owner=receipt.owner or None,
                    effect=graphics_effect(receipt),
                )
            case "sfx":
                audio = self.audio()
                return PropertyState(
                    resource=resource,
                    revision=audio.revision,
                    owner=audio.owner or None,
                    effect=sfx_effect(audio),
                )
            case "hud" | "robot" | "voice" | "face":
                raise AdapterFaultError(resource)
            case _:
                assert_never(resource)

    def apply_visual(
        self,
        settings: VisualSettings,
        expected: PropertyState,
        *,
        duration_ms: int = 30000,
    ) -> str:
        """Owner-authenticated visual request; return a token, never applied state."""
        current = self.snapshot("graphics")
        if current != expected or not self.renderer().source_available:
            raise AdapterFaultError(GRAPHICS)
        receipt = self.renderer()
        owner = uuid4().hex
        wire = RenderRequest.model_validate(
            {
                **settings.model_dump(),
                "consumer_id": receipt.consumer_id,
                "actor_id": self.binding.actor_id,
                "cue_id": owner,
                "owner": owner,
                "expected_owner": receipt.owner,
                "expected_revision": receipt.revision,
                "revision": receipt.revision + 1,
                "issued_ms": self.clock.epoch_ms(),
                "duration_ms": duration_ms,
                "preset": {
                    "rgb.fixed.v1": "rgb",
                    "rgb.crimson.v1": "liquidation",
                    "xyz.depth.v1": "xyz",
                    "xyz.crimson.v1": "xyz",
                }[settings.look],
            }
        )
        self.mailbox.write("effects.json", wire.model_dump_json())
        self.visual_pending = {owner: wire}
        return owner

    def visual_receipt(self, owner: str) -> RenderReceipt | None:
        """Observe the exact owner visual request; caller redacts private metadata."""
        wire = self.visual_pending.get(owner)
        receipt = self.renderer()
        if (
            wire is None
            or receipt.status != "applied"
            or not receipt.source_available
            or receipt.consumer_id != wire.consumer_id
            or receipt.revision != wire.revision
            or receipt.actor_id != self.binding.actor_id
            or receipt.owner != owner
            or receipt.effective != wire
        ):
            return None
        return receipt
