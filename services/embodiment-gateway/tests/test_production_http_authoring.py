"""Real loopback HTTP security and revision tests; explicitly injected fixture."""

import json

from furbomek_gateway.production_http_models import (
    OwnerResult,
)

from .framing_cases import preset
from .production_http_wire import exchange, login, running


def test_visual_payload_preserves_parameters_and_rejects_private_authority() -> None:
    with running() as (server, controller, token):
        headers = login(server, token)
        request = {
            "epoch": "fixture-epoch",
            "revision": 0,
            "action": "visual-apply",
            "duration_ms": 1000,
            "visual": {
                "look": "xyz.crimson.v1",
                "point_pixels": 2.1,
                "zoom": 1.2,
                "yaw": 0.2,
                "pitch": 0.1,
                "hud_visible": False,
                "insets_visible": False,
                "pulse_hz": 0.5,
                "intensity_percent": 37,
            },
        }
        status, body, _ = exchange(
            server,
            "/api/production/action",
            method="POST",
            body=json.dumps(request),
            headers=headers,
        )
        result = OwnerResult.model_validate_json(body)
        assert status == 200
        assert result.state.visual is not None
        assert result.state.visual.look == "xyz.crimson.v1"
        assert result.state.visual.point_pixels == 2.1
        request["actor_id"] = "external"
        request["revision"] = 1
        status, _, _ = exchange(
            server,
            "/api/production/action",
            method="POST",
            body=json.dumps(request),
            headers=headers,
        )
        assert status == 400
        assert controller.calls == 1


def test_invalid_framing_references_never_dispatch() -> None:
    with running() as (server, controller, token):
        framing = preset().model_dump(mode="json")
        framing["fallback"] = "unknown"
        body = json.dumps(
            {
                "epoch": "fixture-epoch",
                "revision": 0,
                "action": "framing-apply",
                "framing": framing,
            }
        )
        status, _, _ = exchange(
            server,
            "/api/production/action",
            method="POST",
            body=body,
            headers=login(server, token),
        )
        assert status == 400
        assert controller.calls == 0


def test_unavailable_visual_adapter_cannot_be_bypassed_by_http() -> None:
    with running() as (server, controller, token):
        controller.state = controller.state.model_copy(
            update={"visual_available": False}
        )
        body = json.dumps(
            {
                "epoch": "fixture-epoch",
                "revision": 0,
                "action": "visual-apply",
                "duration_ms": 1000,
                "visual": {"look": "rgb.fixed.v1"},
            }
        )
        status, _, _ = exchange(
            server,
            "/api/production/action",
            method="POST",
            body=body,
            headers=login(server, token),
        )
        assert status == 409
        assert controller.calls == 0


def test_held_preview_validates_without_applied_state() -> None:
    with running() as (server, controller, token):
        controller.state = controller.state.model_copy(
            update={"health": "held", "visual_available": False}
        )
        body = json.dumps(
            {
                "epoch": "fixture-epoch",
                "revision": 0,
                "action": "visual-preview",
                "duration_ms": 1000,
                "visual": {"look": "rgb.fixed.v1"},
            }
        )
        status, response, _ = exchange(
            server,
            "/api/production/action",
            method="POST",
            body=body,
            headers=login(server, token),
        )
        result = OwnerResult.model_validate_json(response)
        assert status == 200
        assert result.reason == "previewed"
        assert result.state.visual is None
        assert result.state.health == "held"
        assert result.state.revision == 0
