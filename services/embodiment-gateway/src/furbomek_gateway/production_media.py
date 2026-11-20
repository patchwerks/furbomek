"""Real private graphics/SFX ReactionAdapter; submission never implies application."""

from typing import assert_never

from pydantic import ValidationError

from .effect_contracts import (
    AppliedAck,
    FaceEffect,
    GraphicsEffect,
    HudEffect,
    MotionEffect,
    SfxEffect,
    VoiceEffect,
)
from .production_framing import FramingSelection
from .production_mailbox import PrivateMailbox
from .production_media_channel import (
    GRAPHICS,
    RENDER_FRESH_MS,
    MediaBinding,
    MediaChannel,
)
from .production_media_contracts import (
    Framing,
    RenderRequest,
    SfxRequest,
)
from .production_media_release import release_audio, release_graphics
from .reaction_types import (
    AdapterFaultError,
    Clock,
    Dispatch,
    PropertyState,
    StorePrivacyError,
)


class ProductionMedia(MediaChannel):
    """Serialize through one exclusively owned mailbox; no device/OBS control API.

    Poll pending owners with acknowledge(); pass returned receipts to the scheduler.
    Release waits at most 500ms for actual consumer CAS. STOP is owner-scoped and
    never restores or clears another actor's state. Context owns the mailbox lock.
    """

    def __init__(
        self, mailbox: PrivateMailbox, clock: Clock, binding: MediaBinding
    ) -> None:
        """Bind trusted local state; no implicit capability or live process start."""
        super().__init__(mailbox, clock, binding)
        self._pending: dict[str, tuple[Dispatch, RenderRequest | SfxRequest]] = {}
        self._selection: FramingSelection | None = None

    def select_framing(self, selection: FramingSelection) -> None:
        """Accept only the trusted ProductionFraming lane's short-lived decision."""
        if (
            not 0
            < selection.decision.expires_ms - self.clock.monotonic_ms()
            <= RENDER_FRESH_MS
        ):
            raise AdapterFaultError(GRAPHICS)
        self._selection = selection

    def dispatch(self, request: Dispatch) -> None:
        """Fence against actual state, then write once; ACK must be polled later."""
        if request.owner in self._pending or not self.available(request.resource):
            raise AdapterFaultError(request.resource)
        current = self.snapshot(request.resource)
        if (
            current != request.previous
            or self.clock.monotonic_ms() >= request.deadline_ms
        ):
            raise AdapterFaultError(request.resource)
        effect = request.cue.effect
        match effect:
            case GraphicsEffect() if request.resource == "graphics":
                receipt = self.renderer()
                framing = Framing()
                if self._selection is not None:
                    if self.clock.monotonic_ms() >= self._selection.decision.expires_ms:
                        raise AdapterFaultError(GRAPHICS)
                    framing = self._selection.framing.model_copy(
                        update={
                            "valid_until_ms": self.clock.epoch_ms()
                            + self._selection.decision.expires_ms
                            - self.clock.monotonic_ms(),
                        }
                    )
                looks = {
                    "neutral": "rgb.fixed.v1",
                    "rgb": "rgb.fixed.v1",
                    "xyz": "xyz.depth.v1",
                    "liquidation": "rgb.crimson.v1",
                }
                wire = RenderRequest.model_validate(
                    {
                        "consumer_id": receipt.consumer_id,
                        "actor_id": self.binding.actor_id,
                        "cue_id": request.cue.id,
                        "owner": request.owner,
                        "expected_owner": current.owner or "",
                        "expected_revision": current.revision,
                        "revision": current.revision + 1,
                        "issued_ms": self.clock.epoch_ms(),
                        "duration_ms": effect.duration_ms,
                        "look": looks[effect.preset],
                        "preset": effect.preset,
                        "intensity_percent": effect.intensity_percent,
                        "pulse_hz": 1.0 if effect.preset == "liquidation" else 0.0,
                        "framing": framing,
                    }
                )
                self.mailbox.write("effects.json", wire.model_dump_json())
            case SfxEffect() if request.resource == "sfx":
                audio = self.audio()
                wire = SfxRequest(
                    consumer_id=audio.consumer_id,
                    actor_id=self.binding.actor_id,
                    cue_id=request.cue.id,
                    owner=request.owner,
                    expected_owner=current.owner or "none",
                    expected_revision=current.revision,
                    revision=current.revision + 1,
                    issued_ms=self.clock.epoch_ms() // 1000 * 1000,
                    duration_ms=effect.duration_ms,
                    preset=effect.preset,
                    gain_percent=effect.gain_percent,
                )
                self.mailbox.write("sfx.json", wire.model_dump_json())
            case (
                GraphicsEffect()
                | SfxEffect()
                | HudEffect()
                | MotionEffect()
                | VoiceEffect()
                | FaceEffect()
            ):
                raise AdapterFaultError(request.resource)
            case _:
                assert_never(effect)
        self._pending = {
            owner: pending
            for owner, pending in self._pending.items()
            if pending[0].resource != request.resource
        }
        self._pending[request.owner] = (request, wire)

    def acknowledge(self, owner: str) -> AppliedAck | None:
        """Return only an exact, fresh applied revision from the bound consumer."""
        pending = self._pending.get(owner)
        if pending is None:
            return None
        request, wire = pending
        try:
            match wire:
                case RenderRequest():
                    receipt = self.renderer()
                    accepted = (
                        receipt.status == "applied"
                        and receipt.source_available
                        and receipt.effective == wire
                        and receipt.look == wire.look
                    )
                case SfxRequest():
                    receipt = self.audio()
                    accepted = (
                        receipt.status == "playing"
                        and receipt.source_available
                        and not receipt.muted
                        and receipt.preset == wire.preset
                        and receipt.gain_percent == wire.gain_percent
                        and receipt.duration_ms == wire.duration_ms
                    )
                case _:
                    assert_never(wire)
            if (
                not accepted
                or receipt.consumer_id != wire.consumer_id
                or receipt.actor_id != self.binding.actor_id
                or receipt.owner != owner
                or receipt.cue_id != wire.cue_id
                or receipt.revision != wire.revision
            ):
                return None
            return AppliedAck(
                status="applied",
                cue_id=request.cue.id,
                capability=request.cue.effect.capability,
                resource=request.resource,
                owner=owner,
                previous_revision=wire.expected_revision,
                revision=wire.revision,
                effective=request.cue.effect,
                available=True,
            )
        except (OSError, ValidationError, StorePrivacyError, AdapterFaultError):
            return None

    def release(self, state: PropertyState, previous: PropertyState | None) -> bool:
        """Wait for real owner CAS restoration; audio one-shots are never replayed."""
        match state.resource:
            case "graphics":
                return release_graphics(self, state, previous)
            case "sfx":
                return release_audio(self, state)
            case "hud" | "robot" | "voice" | "face":
                return False
            case _:
                assert_never(state.resource)

    def stop(self) -> None:
        """Publish owner-scoped STOP even when another consumer is unavailable.

        A missing receipt cannot confirm stopping; the last bounded lease remains
        the backstop. Replacing a queued apply prevents its later consumption.
        """
        graphics = list(self.visual_pending.values())
        audio_requests: list[SfxRequest] = []
        for _, request in self._pending.values():
            match request:
                case RenderRequest():
                    graphics.append(request)
                case SfxRequest():
                    audio_requests.append(request)
                case _:
                    assert_never(request)
        latest_graphics = sorted(graphics, key=lambda request: request.revision)[-1:]
        for wire in [*latest_graphics, *audio_requests[-1:]]:
            revision = wire.revision
            try:
                match wire:
                    case RenderRequest():
                        revision = self.renderer().revision
                    case SfxRequest():
                        revision = self.audio().revision
                    case _:
                        assert_never(wire)
            except (OSError, ValidationError, StorePrivacyError, AdapterFaultError):
                revision = wire.revision
            stop = wire.model_copy(
                update={
                    "operation": "stop",
                    "expected_owner": wire.owner,
                    "expected_revision": revision,
                    "revision": revision + 1,
                }
            )
            match stop:
                case RenderRequest():
                    self.mailbox.write("effects.json", stop.model_dump_json())
                case SfxRequest():
                    self.mailbox.write("sfx.json", stop.model_dump_json())
                case _:
                    assert_never(stop)
