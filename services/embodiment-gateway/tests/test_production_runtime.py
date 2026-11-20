from pathlib import Path

import pytest

from furbomek_gateway.effect_contracts import GraphicsEffect
from furbomek_gateway.framing_models import Frame, Roi
from furbomek_gateway.production_control import (
    ReactionOperation,
    Status,
)
from furbomek_gateway.production_http_models import (
    EffectRequest,
    FramingRequest,
    OwnerSaved,
    SaveRequest,
)
from furbomek_gateway.production_lifecycle import ProductionLifetime, ProductionSettings
from furbomek_gateway.production_projection import ProductionProjection
from furbomek_gateway.production_saved import SavedPreset
from furbomek_gateway.reaction_types import AdapterFaultError
from tests.framing_cases import frame, preset
from tests.production_media_support import eventually
from tests.production_runtime_support import production

__all__ = ["production"]
EFFECT = GraphicsEffect(
    capability="graphics.pulse.v1",
    preset="liquidation",
    intensity_percent=35,
    duration_ms=10000,
)


def test_unavailable_authoring_persists_without_dispatch(
    production: ProductionLifetime,
) -> None:
    runtime = production.runtime
    _ = (runtime.media.mailbox.directory / "fixture-exit").write_text("stop")
    _ = eventually(
        lambda: runtime.status().health, lambda health: health == "unavailable"
    )
    state = runtime.status()
    assert state.health == "unavailable"
    saved = runtime.execute(
        SaveRequest(
            action="save",
            epoch=state.epoch,
            revision=state.revision,
            saved=OwnerSaved(effect=EFFECT),
        )
    )
    assert saved.reason == "saved"
    assert SavedPreset(runtime.scheduler.store.path.parent).load() == OwnerSaved(
        effect=EFFECT
    )
    rejected = runtime.execute(
        EffectRequest(
            action="apply",
            epoch=saved.state.epoch,
            revision=saved.state.revision,
            effect=EFFECT,
        )
    )
    assert rejected.reason == "unavailable"
    assert not (runtime.media.mailbox.directory / "effects.json").exists()


def test_curated_pack_reaches_actual_consumer_and_sanitized_projection(
    production: ProductionLifetime,
) -> None:
    submitted = production.dispatch.execute(
        ReactionOperation(action="trigger", pack="liquidation"), "local"
    )
    assert submitted.accepted
    assert submitted.event_id is not None
    admitted = min(step.due_ms for step in production.runtime.scheduler.store.steps())
    _ = eventually(
        production.runtime.clock.monotonic_ms, lambda now: now >= admitted + 25
    )

    def observed() -> bool:
        production.runtime.tick()
        return any(
            step.status == "applied" and step.resource == "graphics"
            for step in production.runtime.scheduler.store.steps()
        )

    assert eventually(observed, bool)
    state = production.runtime.status()
    assert isinstance(state.applied, GraphicsEffect)
    assert state.applied.preset == "liquidation"
    projection = ProductionProjection.model_validate_json(
        (
            production.runtime.scheduler.store.path.parent
            / "production-projection.json"
        ).read_bytes()
    )
    assert projection.broker == "HOLD_not_enrolled"
    assert any(
        item.resource == "graphics" and item.status == "applied"
        for item in projection.reactions
    )
    cancelled = production.dispatch.execute(
        ReactionOperation(action="cancel", event_id=submitted.event_id), "local"
    )
    assert cancelled.accepted
    assert not any(step.active for step in production.runtime.scheduler.store.steps())
    assert production.runtime.media.snapshot("graphics").owner is None


def test_restart_loads_configuration_but_never_permission(tmp_path: Path) -> None:
    mailbox = tmp_path / "mailbox"
    mailbox.mkdir(mode=0o700)
    settings = ProductionSettings(
        mailbox=mailbox, state=tmp_path / "private", actor_id="restart-fixture"
    )
    with ProductionLifetime(settings) as first:
        state = first.runtime.status()
        saved = first.runtime.execute(
            SaveRequest(
                action="save",
                epoch=state.epoch,
                revision=state.revision,
                saved=OwnerSaved(effect=EFFECT),
            )
        )
        assert saved.reason == "saved"
        first_epoch = first.runtime.epoch
    with ProductionLifetime(settings) as second:
        state = second.runtime.status()
        assert state.epoch != first_epoch
        assert state.saved == OwnerSaved(effect=EFFECT)
        assert state.applied is None
        assert state.health == "unavailable"
        assert second.dispatch.execute(Status(), "local").stage == "HOLD"
        assert not (mailbox / "effects.json").exists()


def test_trusted_framing_snapshot_reaches_renderer_without_claimed_source(
    production: ProductionLifetime,
) -> None:
    runtime = production.runtime
    state = runtime.status()
    config = preset()
    chosen = runtime.execute(
        FramingRequest(
            action="framing-apply",
            epoch=state.epoch,
            revision=state.revision,
            framing=config,
        )
    )
    assert chosen.reason == "saved"
    # No trusted subject snapshot means the actual policy chooses its fixed fallback.
    applied = runtime.observe(
        Frame(now_ms=runtime.clock.monotonic_ms()), authenticated_sources=frozenset()
    )
    assert applied.reason == "applied"
    receipt = runtime.media.renderer()
    assert receipt.effective is not None
    assert receipt.effective.framing.roi == Roi(x=0.0, y=0.0, width=1.0, height=1.0)
    assert receipt.effective.framing.transition == config.transition
    old_owner = receipt.owner
    with pytest.raises(AdapterFaultError):
        _ = runtime.observe(
            frame(runtime.clock.monotonic_ms()),
            authenticated_sources=frozenset({"wrong-origin"}),
        )
    assert runtime.media.renderer().owner == old_owner


def test_terminal_stop_never_rearms_from_owner_request(
    production: ProductionLifetime,
) -> None:
    runtime = production.runtime
    state = runtime.status()
    applied = runtime.execute(
        EffectRequest(
            action="apply", epoch=state.epoch, revision=state.revision, effect=EFFECT
        )
    )
    assert applied.reason == "applied"
    runtime.close()
    state = runtime.status()
    rejected = runtime.execute(
        EffectRequest(
            action="apply", epoch=state.epoch, revision=state.revision, effect=EFFECT
        )
    )
    assert rejected.reason == "held"
    reaction = production.dispatch.execute(
        ReactionOperation(action="trigger", pack="liquidation"), "local"
    )
    assert reaction.accepted is False
    assert reaction.reason == "held"
