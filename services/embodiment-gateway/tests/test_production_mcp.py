import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import anyio
import httpx
import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic import TypeAdapter

from furbomek_gateway.edge_protocol import EdgeReply
from furbomek_gateway.effect_contracts import GraphicsEffect
from furbomek_gateway.production_http_models import (
    EffectRequest,
    FramingRequest,
    OwnerState,
    SimpleRequest,
)
from furbomek_gateway.production_lifecycle import ProductionLifetime
from tests.framing_cases import preset
from tests.production_runtime_support import edge, production

__all__ = ["production"]
PROJECT = Path(__file__).resolve().parents[1]
EFFECT = GraphicsEffect(
    capability="graphics.pulse.v1",
    preset="liquidation",
    intensity_percent=35,
    duration_ms=10000,
)


async def _owner_session(client: httpx.AsyncClient) -> str:
    unauthenticated = await client.get("/api/production/status")
    assert unauthenticated.status_code == 401
    cross_origin = await client.post(
        "/api/production/session",
        content="{}",
        headers={
            "Content-Type": "application/json",
            "Origin": "https://example.invalid",
        },
    )
    assert cross_origin.status_code == 403
    bootstrap = await client.post(
        "/api/production/session",
        content="{}",
        headers={
            "Content-Type": "application/json",
            "Authorization": ("Bearer fixture-owner-bootstrap-secret-at-least32"),
        },
    )
    assert bootstrap.status_code == 200
    return TypeAdapter(dict[str, str]).validate_json(bootstrap.content)["csrf"]


@pytest.mark.anyio
async def test_real_stdio_owner_http_share_observed_ack_and_revision(
    production: ProductionLifetime, tmp_path: Path
) -> None:
    host = edge(production, tmp_path)
    with TemporaryDirectory(prefix="p14-") as directory:
        socket = Path(directory) / "control"
        params = StdioServerParameters(
            command=sys.executable,
            args=[
                "-m",
                "furbomek_gateway",
                "edge-mcp",
                str(socket),
                "--production",
            ],
            cwd=PROJECT,
        )
        async with (
            await anyio.create_unix_listener(socket, mode=0o600) as listener,
            anyio.create_task_group() as tasks,
        ):
            _ = tasks.start_soon(listener.serve, host.run_remote)
            async with (
                stdio_client(params) as (read, write),
                ClientSession(read, write) as session,
            ):
                _ = await session.initialize()
                result = await session.call_tool("production_status")
                initial = EdgeReply.model_validate_json(
                    json.dumps(result.structuredContent)
                )
                assert initial.production is not None
                assert initial.production.stage == "HOLD"
                state = initial.production.state
                held = await session.call_tool(
                    "production_movement",
                    {
                        "request": {
                            "steps": [
                                {"profile_id": "not-a-permit", "action": "forward"}
                            ],
                            "duration_ms": 100,
                        }
                    },
                )
                movement = EdgeReply.model_validate_json(
                    json.dumps(held.structuredContent)
                )
                assert movement.production is not None
                assert movement.production.accepted is False
                assert movement.production.stage == "HOLD"
                preview = await session.call_tool(
                    "production_effect",
                    {
                        "request": FramingRequest(
                            action="framing-preview",
                            epoch=state.epoch,
                            revision=state.revision,
                            framing=preset(),
                        ).model_dump(mode="json")
                    },
                )
                assert preview.isError is False
                applied = await session.call_tool(
                    "production_effect",
                    {
                        "request": EffectRequest(
                            action="apply",
                            epoch=state.epoch,
                            revision=state.revision,
                            effect=EFFECT,
                        ).model_dump(mode="json")
                    },
                )
                reply = EdgeReply.model_validate_json(
                    json.dumps(applied.structuredContent)
                )
                assert reply.production is not None
                assert reply.production.result is not None
                assert reply.production.result.reason == "applied"
                assert reply.production.state.receipt is not None
                assert reply.production.state.applied == EFFECT
                assert reply.production.state.receipt.revision > 0
                stale = await session.call_tool(
                    "production_effect",
                    {
                        "request": EffectRequest(
                            action="apply",
                            epoch=state.epoch,
                            revision=state.revision,
                            effect=EFFECT,
                        ).model_dump(mode="json")
                    },
                )
                stale_reply = EdgeReply.model_validate_json(
                    json.dumps(stale.structuredContent)
                )
                assert stale_reply.production is not None
                assert stale_reply.production.result is not None
                assert stale_reply.production.result.reason == "stale"
                assert production.http is not None
                async with httpx.AsyncClient(
                    base_url=production.http.origin,
                    headers={"Origin": production.http.origin},
                ) as client:
                    csrf = await _owner_session(client)
                    observed = await client.get("/api/production/status")
                    live = OwnerState.model_validate_json(observed.content)
                    assert live == reply.production.state
                    denied = await client.post(
                        "/api/production/action",
                        content=SimpleRequest(
                            action="revert", epoch=state.epoch, revision=state.revision
                        ).model_dump_json(),
                        headers={
                            "Content-Type": "application/json",
                            "X-CSRF-Token": csrf,
                        },
                    )
                    assert denied.status_code == 409
                reverted = await session.call_tool(
                    "production_effect",
                    {
                        "request": SimpleRequest(
                            action="revert", epoch=live.epoch, revision=live.revision
                        ).model_dump(mode="json")
                    },
                )
                released = EdgeReply.model_validate_json(
                    json.dumps(reverted.structuredContent)
                )
                assert released.production is not None
                assert released.production.result is not None
                assert released.production.result.reason == "reverted"
                assert released.production.state.applied is None
                assert released.production.state.revision > live.revision
            tasks.cancel_scope.cancel()


@pytest.mark.anyio
async def test_default_stdio_keeps_seven_legacy_tools() -> None:
    params = StdioServerParameters(
        command=sys.executable,
        args=[
            "-m",
            "furbomek_gateway",
            "edge-mcp",
            "/private/tmp/not-an-active-edge.sock",
        ],
        cwd=PROJECT,
    )
    async with (
        stdio_client(params) as (read, write),
        ClientSession(read, write) as session,
    ):
        _ = await session.initialize()
        names = {tool.name for tool in (await session.list_tools()).tools}
        assert names == {
            "robot_get_state",
            "robot_get_supply_voltage",
            "robot_get_capabilities",
            "robot_perform_action",
            "robot_stop",
            "kinect_control",
            "obs_control",
        }
