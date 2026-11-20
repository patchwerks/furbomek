"""Single typed dispatch surface shared by local and authenticated remote peers."""

from typing import Literal, assert_never, final
from uuid import uuid4

from .effect_contracts import CAPABILITIES, Contract, Identifier
from .production_control import (
    Movement,
    Operation,
    OwnerOperation,
    PresetApply,
    ProductionReply,
    ReactionOperation,
    SourceDelivery,
    Status,
)
from .production_framing import ProductionFraming
from .production_http_models import EffectRequest, SimpleRequest
from .production_runtime import ProductionRuntime
from .reaction_contracts import PrivateEvent, ReactionPack


class SourceBinding(Contract):
    """Trusted startup configuration for one authenticated transport principal."""

    source: Identifier
    scope: Identifier


@final
class ProductionDispatch:
    """No provider-selected priority, pack graph, transport identity or rearm."""

    def __init__(
        self,
        runtime: ProductionRuntime,
        packs: tuple[ReactionPack, ...],
        remote_source: SourceBinding | None = None,
        local_source: SourceBinding | None = None,
    ) -> None:
        """Resolve only operator-configured immutable packs."""
        self.runtime = runtime
        self.packs = {pack.pack_id: pack for pack in packs}
        self.bindings = {"remote": remote_source, "local": local_source}

    def reply(
        self,
        *,
        accepted: bool = True,
        reason: str = "observed",
        event_id: int | None = None,
        pack: ReactionPack | None = None,
    ) -> ProductionReply:
        """Project no private event identities or provider values."""
        return ProductionReply.model_validate(
            {
                "state": self.runtime.status(),
                "catalog": tuple(
                    definition.model_copy(
                        update={
                            "available": definition.available
                            and self.runtime.media.available(definition.resource)
                        }
                    )
                    for definition in CAPABILITIES
                ),
                "reactions": self.runtime.scheduler.projection()[-64:],
                "accepted": accepted,
                "reason": reason,
                "event_id": event_id,
                "pack": pack,
            }
        )

    def execute(
        self, operation: Operation, origin: Literal["remote", "local"]
    ) -> ProductionReply:
        """Bind transport origin outside request data before any admission."""
        runtime = self.runtime
        with runtime.gate:
            match operation:
                case Movement():
                    return self.reply(accepted=False, reason="held")
                case Status():
                    return self.reply()
                case OwnerOperation():
                    result = runtime.execute(operation.request)
                    return self.reply().model_copy(
                        update={
                            "result": result,
                            "accepted": result.outcome == "accepted",
                        }
                    )
                case PresetApply():
                    return self._preset(operation)
                case SourceDelivery():
                    return self._source(operation, origin)
                case ReactionOperation():
                    return self._reaction(operation)
                case _:
                    assert_never(operation)

    def cancel_reply(self, reply: ProductionReply) -> None:
        """Peer-loss cleanup targets only the exact completed request ownership."""
        with self.runtime.gate:
            if reply.event_id is not None:
                self.runtime.scheduler.cancel(reply.event_id, "peer_disconnected")
            if reply.result is not None and reply.result.reason == "applied":
                _ = self.runtime.execute(
                    SimpleRequest(
                        action="cancel",
                        epoch=reply.state.epoch,
                        revision=reply.state.revision,
                    )
                )

    def _preset(self, operation: PresetApply) -> ProductionReply:
        runtime = self.runtime
        if runtime.saved is None:
            return self.reply(accepted=False, reason="held")
        result = runtime.execute(
            EffectRequest(
                action="apply",
                epoch=operation.epoch,
                revision=operation.revision,
                effect=runtime.saved.effect,
            )
        )
        if result.outcome == "accepted" and runtime.saved.framing is not None:
            runtime.framing = ProductionFraming(runtime.saved.framing, runtime.clock)
            runtime.revision += 1
            result = result.model_copy(update={"state": runtime.status()})
        return self.reply().model_copy(
            update={"result": result, "accepted": result.outcome == "accepted"}
        )

    def _source(
        self, operation: SourceDelivery, origin: Literal["remote", "local"]
    ) -> ProductionReply:
        runtime = self.runtime
        binding = self.bindings[origin]
        event = operation.receipt.event
        if (
            binding is None
            or event.source != binding.source
            or event.scope != binding.scope
        ):
            return self.reply(accepted=False, reason="origin")
        if not runtime.scheduler.enabled:
            return self.reply(accepted=False, reason="held")
        names = {
            "acknowledge": "viewer-reaction",
            "liquidation": "liquidation",
            "rgb": "rgb",
            "xyz": "xyz",
        }
        pack = self.packs.get(names[operation.receipt.intent])
        if pack is None:
            return self.reply(accepted=False, reason="unknown_pack")
        try:
            event_id = runtime.scheduler.submit(event, pack)
        except ValueError:
            return self.reply(accepted=False, reason="stale")
        return self.reply(
            accepted=event_id is not None,
            reason="submitted" if event_id is not None else "duplicate",
            event_id=event_id,
        )

    def _reaction(self, operation: ReactionOperation) -> ProductionReply:
        runtime = self.runtime
        match operation.action:
            case "status":
                return self.reply()
            case "cancel":
                if operation.event_id is None:
                    return self.reply(accepted=False, reason="held")
                runtime.scheduler.cancel(operation.event_id)
                return self.reply(reason="cancelled")
            case "preview" | "trigger":
                pack = self.packs.get(operation.pack or "")
                if pack is None:
                    return self.reply(accepted=False, reason="unknown_pack")
                if operation.action == "preview":
                    return self.reply(reason="previewed", pack=pack)
                now = runtime.clock.epoch_ms()
                identity = uuid4().hex
                event = PrivateEvent(
                    source="owner",
                    scope=runtime.epoch,
                    stable_id=identity,
                    causation_id=identity,
                    origin="adapter",
                    occurred_ms=now,
                    received_ms=now,
                )
                event_id = runtime.scheduler.submit(event, pack)
                return self.reply(
                    accepted=event_id is not None,
                    reason="submitted" if event_id is not None else "held",
                    event_id=event_id,
                )
            case _:
                assert_never(operation.action)
