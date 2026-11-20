import os
import signal
from pathlib import Path
from tempfile import TemporaryDirectory

import anyio
import pytest

from furbomek_gateway.edge_protocol import OperatorRequest, exchange, unix_ms
from furbomek_gateway.effect_contracts import GraphicsEffect
from furbomek_gateway.production_control import (
    OwnerOperation,
    ProductionRequest,
    SourceDelivery,
)
from furbomek_gateway.production_dispatch import SourceBinding
from furbomek_gateway.production_http_models import (
    EffectRequest,
)
from furbomek_gateway.production_lifecycle import ProductionLifetime
from furbomek_gateway.production_sources.contracts import SourceReceipt
from furbomek_gateway.reaction_contracts import PrivateEvent
from furbomek_gateway.reaction_types import PropertyState
from tests.production_media_support import eventually
from tests.production_runtime_support import edge, production

__all__ = ["production"]
EFFECT = GraphicsEffect(
    capability="graphics.pulse.v1",
    preset="liquidation",
    intensity_percent=35,
    duration_ms=10000,
)


@pytest.mark.anyio
async def test_socket_rejects_origins_roles_malformed_and_rearm(
    production: ProductionLifetime, tmp_path: Path
) -> None:
    host = edge(production, tmp_path)
    now = unix_ms()
    event = PrivateEvent(
        source="twitch",
        scope="fixture-channel",
        stable_id="1",
        causation_id="1",
        origin="adapter",
        occurred_ms=now,
        received_ms=now,
    )
    delivery = SourceDelivery(
        receipt=SourceReceipt(
            event=event, intent="acknowledge", preview="Audience preset requested"
        )
    )
    production.dispatch.bindings["local"] = SourceBinding(
        source="twitch", scope="fixture-channel"
    )
    with TemporaryDirectory(prefix="p14-") as directory:
        socket = Path(directory) / "control"
        async with (
            await anyio.create_unix_listener(socket, mode=0o600) as listener,
            anyio.create_task_group() as tasks,
        ):
            _ = tasks.start_soon(listener.serve, host.run_remote)
            refused = await exchange(
                socket, ProductionRequest(issued_ms=now, operation=delivery)
            )
            assert refused.production is not None
            assert refused.production.reason == "origin"
            operator = await exchange(
                socket, OperatorRequest(command="enable", issued_ms=now)
            )
            assert operator.result == "invalid"
            async with await anyio.connect_unix(socket) as peer:
                await peer.send(
                    b'{"target":"production","issued_ms":0,"operation":{"command":"rearm"}}\n'
                )
                assert b'"result":"invalid"' in await peer.receive()
            local = await host.operator(
                ProductionRequest(issued_ms=now, operation=delivery)
                .model_dump_json()
                .encode()
            )
            assert local.production is not None
            assert local.production.accepted
            steps = production.runtime.scheduler.store.steps()
            assert steps[0].cue.effect.capability == "hud.redacted.v1"
            assert all(
                step.cue.effect.capability != "motion.qualified.v1" for step in steps
            )
            duplicate = await host.operator(
                ProductionRequest(issued_ms=now, operation=delivery)
                .model_dump_json()
                .encode()
            )
            assert duplicate.production is not None
            assert duplicate.production.reason == "duplicate"
            tasks.cancel_scope.cancel()


@pytest.mark.anyio
async def test_disconnect_releases_only_its_inflight_effect(
    production: ProductionLifetime, tmp_path: Path
) -> None:
    host = edge(production, tmp_path)
    state = production.runtime.status()
    before = production.runtime.media.snapshot("graphics").revision
    request = ProductionRequest(
        issued_ms=unix_ms(),
        operation=OwnerOperation(
            request=EffectRequest(
                action="apply",
                epoch=state.epoch,
                revision=state.revision,
                effect=EFFECT,
            )
        ),
    )
    consumer = int((tmp_path / "consumer.pid").read_text())
    os.kill(consumer, signal.SIGSTOP)
    try:
        with TemporaryDirectory(prefix="p14-") as directory:
            socket = Path(directory) / "control"
            async with (
                await anyio.create_unix_listener(socket, mode=0o600) as listener,
                anyio.create_task_group() as tasks,
            ):
                _ = tasks.start_soon(listener.serve, host.run_remote)
                async with await anyio.connect_unix(socket) as client:
                    await client.send(request.model_dump_json().encode() + b"\n")
                    _ = await anyio.to_thread.run_sync(
                        eventually,
                        (
                            production.runtime.media.mailbox.directory / "effects.json"
                        ).exists,
                        bool,
                    )
                os.kill(consumer, signal.SIGCONT)

                def wait_released() -> PropertyState:
                    return eventually(
                        lambda: production.runtime.media.snapshot("graphics"),
                        lambda current: (
                            current.revision == before + 2 and current.owner is None
                        ),
                    )

                _ = await anyio.to_thread.run_sync(wait_released)
                tasks.cancel_scope.cancel()
    finally:
        os.kill(consumer, signal.SIGCONT)


def test_missing_ack_consumes_revision_without_claiming_application(
    production: ProductionLifetime, tmp_path: Path
) -> None:
    runtime = production.runtime
    state = runtime.status()
    consumer = int((tmp_path / "consumer.pid").read_text())
    os.kill(consumer, signal.SIGSTOP)
    try:
        request = EffectRequest(
            action="apply", epoch=state.epoch, revision=state.revision, effect=EFFECT
        )
        uncertain = runtime.execute(request)
        assert uncertain.reason == "held"
        assert uncertain.state.receipt is None
        assert uncertain.state.applied is None
        assert uncertain.state.revision > state.revision
        retry = runtime.execute(request)
        assert retry.reason == "stale"
    finally:
        os.kill(consumer, signal.SIGCONT)
