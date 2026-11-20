"""Real loopback HTTP security and revision tests; explicitly injected fixture."""

import json

import pytest

from furbomek_gateway.effect_contracts import (
    GraphicsEffect,
)
from furbomek_gateway.production_http_models import (
    OwnerResult,
    OwnerState,
)

from .production_http_wire import effect_request, exchange, login, running


def test_authenticated_apply_returns_observed_receipt_and_status() -> None:
    with running() as (server, controller, token):
        headers = login(server, token)
        status, body, _ = exchange(
            server,
            "/api/production/action",
            method="POST",
            body=effect_request(),
            headers=headers,
        )
        result = OwnerResult.model_validate_json(body)
        assert status == 200
        assert result.state.revision == 1
        assert result.state.receipt is not None
        assert result.state.receipt.effective == GraphicsEffect(
            capability="graphics.pulse.v1",
            preset="rgb",
            intensity_percent=37,
            duration_ms=1000,
        )
        read_status, observed, _ = exchange(
            server, "/api/production/status", headers=headers
        )
        assert read_status == 200
        assert OwnerState.model_validate_json(observed) == result.state
        assert controller.calls == 1


@pytest.mark.parametrize(
    ("change", "expected"),
    [
        ({"Origin": "http://evil.invalid"}, 403),
        ({"Host": "evil.invalid"}, 403),
        ({"X-CSRF-Token": "wrong"}, 403),
        ({"Cookie": "production_owner=wrong"}, 401),
        ({"Sec-Fetch-Mode": "navigate"}, 403),
        ({"Sec-Fetch-Site": "cross-site"}, 403),
    ],
)
def test_untrusted_requests_never_reach_controller(
    change: dict[str, str], expected: int
) -> None:
    with running() as (server, controller, token):
        headers = {**login(server, token), **change}
        status, _, _ = exchange(
            server,
            "/api/production/action",
            method="POST",
            body=effect_request(),
            headers=headers,
        )
        assert status == expected
        assert controller.calls == 0


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        (effect_request(revision=99), 409),
        (effect_request(action="navigate"), 400),
        (effect_request().replace('"duration_ms": 1000', '"duration_ms": 30001'), 400),
        (
            effect_request().replace(
                '"action": "apply"', '"role": "operator", "action": "apply"'
            ),
            400,
        ),
        (effect_request().replace('"graphics.pulse.v1"', '"motion.qualified.v1"'), 400),
        ("x" * 32769, 413),
    ],
)
def test_stale_unknown_physical_role_and_excess_refused(
    body: str, expected: int
) -> None:
    with running() as (server, controller, token):
        status, _, _ = exchange(
            server,
            "/api/production/action",
            method="POST",
            body=body,
            headers=login(server, token),
        )
        assert status == expected
        assert controller.calls == 0


def test_held_and_busy_do_not_dispatch() -> None:
    with running() as (server, controller, token):
        headers = login(server, token)
        controller.state = controller.state.model_copy(update={"health": "held"})
        status, body, _ = exchange(
            server,
            "/api/production/action",
            method="POST",
            body=effect_request(),
            headers=headers,
        )
        assert status == 409
        assert json.loads(body) == {"error": "held"}
        with server.operation:
            status, body, _ = exchange(
                server, "/api/production/status", headers=headers
            )
        assert status == 409
        assert json.loads(body) == {"error": "busy"}
        assert controller.calls == 0


def test_bootstrap_is_explicit_and_sessions_bounded() -> None:
    with running(session_limit=1) as (server, _, token):
        status, _, _ = exchange(server, "/api/production/status")
        assert status == 401
        _ = login(server, token)
        status, _, _ = exchange(
            server,
            "/api/production/session",
            method="POST",
            body="{}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert status == 401


def test_expired_cookie_and_csrf_are_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    with running() as (server, controller, token):
        headers = login(server, token)
        monkeypatch.setattr(
            "furbomek_gateway.production_http_sessions.time.monotonic", lambda: 10**15
        )
        status, _, _ = exchange(
            server,
            "/api/production/action",
            method="POST",
            body=effect_request(),
            headers=headers,
        )
        assert status == 401
        assert controller.calls == 0


def test_status_has_no_write_and_unknown_paths_reject() -> None:
    with running() as (server, controller, token):
        headers = login(server, token)
        for path in [
            "/api/production/status?token=ignored",
            "/api/production/rearm",
            "/api/production/../status",
        ]:
            status, _, _ = exchange(server, path, headers=headers)
            assert status == 404
        assert controller.calls == 0


def test_wrong_bootstrap_cannot_create_session() -> None:
    with running() as (server, controller, _):
        status, _, headers = exchange(
            server,
            "/api/production/session",
            method="POST",
            body="{}",
            headers={"Authorization": "Bearer incorrect"},
        )
        assert status == 401
        assert "Set-Cookie" not in headers
        assert controller.calls == 0


@pytest.mark.parametrize("length", ["9" * 5000, "²"])
def test_invalid_length_header_rejected_without_integer_conversion_error(
    length: str,
) -> None:
    with running() as (server, controller, token):
        status, _, _ = exchange(
            server,
            "/api/production/action",
            method="POST",
            body="{}",
            headers={**login(server, token), "Content-Length": length},
        )
        assert status == 413
        assert controller.calls == 0


def test_preview_does_not_apply_and_revert_restores_previous_observation() -> None:
    with running() as (server, _, token):
        headers = login(server, token)
        status, body, _ = exchange(
            server,
            "/api/production/action",
            method="POST",
            body=effect_request(action="preview"),
            headers=headers,
        )
        assert status == 200
        assert OwnerResult.model_validate_json(body).state.applied is None
        for revision, intensity in [(0, 37), (1, 62)]:
            status, _, _ = exchange(
                server,
                "/api/production/action",
                method="POST",
                body=effect_request(revision=revision).replace(
                    '"intensity_percent": 37', f'"intensity_percent": {intensity}'
                ),
                headers=headers,
            )
            assert status == 200
        status, body, _ = exchange(
            server,
            "/api/production/action",
            method="POST",
            body='{"epoch":"fixture-epoch","revision":2,"action":"revert"}',
            headers=headers,
        )
        result = OwnerResult.model_validate_json(body)
        assert status == 200
        assert result.reason == "reverted"
        assert isinstance(result.state.applied, GraphicsEffect)
        assert result.state.applied.intensity_percent == 37
        assert result.state.revision == 3
