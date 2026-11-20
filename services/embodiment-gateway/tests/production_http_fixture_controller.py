"""Test-only observed state machine; never installed as a runtime default."""

from furbomek_gateway.effect_contracts import AppliedAck, capability_definition
from furbomek_gateway.production_http_models import (
    EffectRequest,
    FramingRequest,
    OwnerAction,
    OwnerResult,
    OwnerState,
    SaveRequest,
    SimpleRequest,
    VisualRequest,
)


class FixtureController:
    """Test-only state machine; no runtime or device is connected."""

    def __init__(self) -> None:
        self.state: OwnerState = OwnerState(
            origin="injected-test-fixture",
            epoch="fixture-epoch",
            revision=0,
            health="fresh",
            visual_available=True,
            framing_available=True,
            reason="observed",
        )
        self.calls: int = 0

    def status(self) -> OwnerState:
        return self.state

    def execute(self, request: OwnerAction) -> OwnerResult:
        self.calls += 1
        if isinstance(request, EffectRequest):
            return self.effect(request)
        if isinstance(request, SaveRequest):
            self.state = self.state.model_copy(
                update={"saved": request.saved, "revision": self.state.revision + 1}
            )
            return OwnerResult(outcome="accepted", reason="saved", state=self.state)
        if isinstance(request, VisualRequest):
            return self.visual(request)
        if isinstance(request, FramingRequest):
            return self.framing(request)
        if isinstance(request, SimpleRequest):
            return self.simple(request)
        return OwnerResult(outcome="rejected", reason="unsupported", state=self.state)

    def effect(self, request: EffectRequest) -> OwnerResult:
        if request.action == "preview":
            return OwnerResult(
                outcome="accepted",
                reason="previewed",
                state=self.state,
                preview=request.effect,
            )
        revision = self.state.revision + 1
        receipt = AppliedAck(
            status="applied",
            cue_id="http-fixture",
            capability=request.effect.capability,
            resource=capability_definition(request.effect.capability).resource,
            owner="fixture",
            previous_revision=self.state.revision,
            revision=revision,
            effective=request.effect,
            available=True,
        )
        self.state = self.state.model_copy(
            update={
                "revision": revision,
                "applied": request.effect,
                "previous": self.state.applied,
                "receipt": receipt,
            }
        )
        return OwnerResult(outcome="accepted", reason="applied", state=self.state)

    def visual(self, request: VisualRequest) -> OwnerResult:
        if request.action == "visual-preview":
            return OwnerResult(
                outcome="accepted",
                reason="previewed",
                state=self.state,
                visual_preview=request.visual,
            )
        self.state = self.state.model_copy(
            update={"visual": request.visual, "revision": self.state.revision + 1}
        )
        return OwnerResult(outcome="accepted", reason="applied", state=self.state)

    def framing(self, request: FramingRequest) -> OwnerResult:
        if request.action == "framing-preview":
            return OwnerResult(
                outcome="accepted",
                reason="previewed",
                state=self.state,
                framing_preview=request.framing,
            )
        self.state = self.state.model_copy(
            update={"framing": request.framing, "revision": self.state.revision + 1}
        )
        return OwnerResult(
            outcome="accepted",
            reason="saved" if request.action == "framing-save" else "applied",
            state=self.state,
        )

    def simple(self, request: SimpleRequest) -> OwnerResult:
        if request.action == "cancel":
            return OwnerResult(outcome="accepted", reason="cancelled", state=self.state)
        if self.state.previous is None:
            return OwnerResult(
                outcome="rejected", reason="unsupported", state=self.state
            )
        result = self.effect(
            EffectRequest(
                action="apply",
                epoch=request.epoch,
                revision=request.revision,
                effect=self.state.previous,
            )
        )
        return result.model_copy(update={"reason": "reverted"})
