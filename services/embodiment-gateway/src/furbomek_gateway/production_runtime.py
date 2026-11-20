"""One private production owner, shared by HTTP and semantic MCP transports."""

from threading import RLock
from typing import assert_never, final
from uuid import uuid4

from pydantic import ValidationError

from .effect_contracts import GraphicsEffect
from .framing_models import Frame
from .production_effect_owner import NEUTRAL, EffectOwner
from .production_framing import ProductionFraming
from .production_http_models import (
    EffectRequest,
    FramingRequest,
    ManualRequest,
    OwnerAction,
    OwnerResult,
    OwnerSaved,
    OwnerState,
    SaveRequest,
    SimpleRequest,
    VisualRequest,
)
from .production_media import ProductionMedia
from .production_owner_state import OwnerObservation
from .production_projection import ProductionProjection, publish
from .production_saved import SavedPreset
from .reaction_scheduler import ReactionScheduler
from .reaction_types import (
    AdapterFaultError,
    Clock,
    StorePrivacyError,
)


@final
class ProductionRuntime:
    """Serialize all writers and expire observations; no physical release authority.

    Media and durable scheduler are mandatory real dependencies. Startup never
    resumes owner effects or imports a saved preset as authorization.
    """

    def __init__(
        self, media: ProductionMedia, scheduler: ReactionScheduler, clock: Clock
    ) -> None:
        """Bind a single host clock and existing private media owner."""
        self.media = media
        self.scheduler = scheduler
        self.clock = clock
        self.gate = RLock()
        self.epoch = uuid4().hex
        self.revision = 0
        self.effects = EffectOwner(media, clock)
        self.presets = SavedPreset(scheduler.store.path.parent)
        self.saved: OwnerSaved | None = self.presets.load()
        self.framing: ProductionFraming | None = None
        self.observation = OwnerObservation(media, self.effects)
        self._publish()

    def status(self) -> OwnerState:
        """Return fresh consumer observations, never last submitted intent."""
        with self.gate:
            state = self.observation.read(
                epoch=self.epoch,
                revision=self.revision,
                saved=self.saved,
                framing=self.framing,
            )
            self.revision = state.revision
            return state

    def result(self, reason: str, *, accepted: bool = False) -> OwnerResult:
        """Construct a closed result at the controller boundary."""
        return OwnerResult.model_validate(
            {
                "outcome": "accepted" if accepted else "rejected",
                "reason": reason,
                "state": self.status(),
            }
        )

    def execute(self, request: OwnerAction) -> OwnerResult:
        """Fence HTTP and MCP together, then perform only the typed operation."""
        with self.gate:
            state = self.status()
            if request.epoch != self.epoch or request.revision != self.revision:
                return self.result("stale")
            try:
                authored = self._author(request, state)
                if authored is not None:
                    return authored
                if not self.scheduler.enabled:
                    return self.result("held")
                if state.health != "fresh":
                    return self.result("unavailable")
                return self._mutate(request)
            except (OSError, ValidationError, AdapterFaultError, StorePrivacyError):
                return self.result("unavailable")

    def _mutate(self, request: OwnerAction) -> OwnerResult:
        """Execute operations whose live media gate has passed."""
        match request:
            case (
                EffectRequest(action="apply")
                | SimpleRequest(action="revert")
                | VisualRequest(action="visual-apply")
            ):
                return self._effect(request)
            case FramingRequest(action="framing-apply"):
                self.framing = ProductionFraming(request.framing, self.clock)
                self.revision += 1
                # Configuration selected; no frame or renderer ACK yet.
                return self.result("saved", accepted=True)
            case ManualRequest():
                return self._manual(request)
            case (
                EffectRequest()
                | SimpleRequest()
                | VisualRequest()
                | FramingRequest()
                | SaveRequest()
            ):
                return self.result("unsupported")
            case _:
                assert_never(request)

    def _author(self, request: OwnerAction, state: OwnerState) -> OwnerResult | None:
        """Safe authoring never requires a live renderer or dispatch authority."""
        match request:
            case EffectRequest(action="preview"):
                return OwnerResult(
                    outcome="accepted",
                    reason="previewed",
                    state=state,
                    preview=request.effect,
                )
            case VisualRequest(action="visual-preview"):
                return OwnerResult(
                    outcome="accepted",
                    reason="previewed",
                    state=state,
                    visual_preview=request.visual,
                )
            case FramingRequest(action="framing-preview"):
                return OwnerResult(
                    outcome="accepted",
                    reason="previewed",
                    state=state,
                    framing_preview=request.framing,
                )
            case SaveRequest() | FramingRequest(action="framing-save"):
                return self._save(request)
            case SimpleRequest(action="cancel"):
                return self._effect(request)
            case (
                EffectRequest()
                | VisualRequest()
                | FramingRequest()
                | ManualRequest()
                | SimpleRequest()
            ):
                return None
            case _:
                assert_never(request)

    def _effect(
        self, request: EffectRequest | VisualRequest | SimpleRequest
    ) -> OwnerResult:
        before = self.effects.revision
        try:
            match request:
                case EffectRequest():
                    outcome = self.effects.apply(request)
                case VisualRequest():
                    outcome = self.effects.visual(request)
                case SimpleRequest():
                    outcome = self.effects.release(restore=request.action == "revert")
                case _:
                    assert_never(request)
        finally:
            self.revision += self.effects.revision - before
        return self.result(
            outcome, accepted=outcome in ("applied", "reverted", "cancelled")
        )

    def _manual(self, request: ManualRequest) -> OwnerResult:
        if self.framing is None:
            return self.result("unavailable")
        try:
            self.framing.override(request.manual)
        except ValueError:
            return self.result("unsupported")
        self.revision += 1
        return self.result("saved", accepted=True)

    def _save(self, request: SaveRequest | FramingRequest) -> OwnerResult:
        match request:
            case SaveRequest():
                saved = request.saved
            case FramingRequest():
                if self.saved is None:
                    return self.result("held")
                saved = self.saved.model_copy(update={"framing": request.framing})
            case _:
                assert_never(request)
        self.presets.save(saved)
        self.saved = saved
        self.revision += 1
        return self.result("saved", accepted=True)

    def observe(
        self, frame: Frame, *, authenticated_sources: frozenset[str]
    ) -> OwnerResult:
        """Trusted local adapter only; never exposed as an owner/MCP request DTO."""
        with self.gate:
            if self.framing is None:
                return self.result("held")
            if any(
                signal.source not in authenticated_sources for signal in frame.signals
            ):
                resource = "graphics"
                raise AdapterFaultError(resource)
            self.media.select_framing(self.framing.step(frame))
            state = self.status()
            effect = (
                state.applied if isinstance(state.applied, GraphicsEffect) else NEUTRAL
            )
            return self.execute(
                EffectRequest(
                    action="apply",
                    epoch=self.epoch,
                    revision=self.revision,
                    effect=effect,
                )
            )

    def tick(self) -> None:
        """Advance the actual durable scheduler and consume exact media ACKs."""
        with self.gate:
            if (
                self.effects.current is not None
                and self.clock.monotonic_ms() < self.effects.owner_until_ms
            ):
                self._publish()
                return
            self.scheduler.tick()
            for step in self.scheduler.store.steps():
                if step.status == "dispatched":
                    ack = self.media.acknowledge(step.owner)
                    if ack is not None:
                        _ = self.scheduler.acknowledge(ack)
            self._publish()

    def _publish(self) -> None:
        publish(
            self.scheduler.store.path.parent,
            ProductionProjection(
                published_ms=self.clock.epoch_ms(),
                reactions=self.scheduler.projection()[-64:],
            ),
        )

    def close(self) -> None:
        """Cancel owned bounded outputs; never clear or grant physical authority."""
        with self.gate:
            self.scheduler.stop()
            self._publish()
