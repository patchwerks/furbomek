"""Real loopback HTTP security and revision tests; explicitly injected fixture."""

import json
import secrets
from collections.abc import Generator
from contextlib import contextmanager
from http.client import HTTPConnection
from pathlib import Path
from threading import Thread

from pydantic import SecretStr, TypeAdapter

from furbomek_gateway.production_http import OwnerHttpServer

from .production_http_fixture_controller import FixtureController


@contextmanager
def running(
    *, session_limit: int = 8, studio_directory: Path | None = None
) -> Generator[tuple[OwnerHttpServer, FixtureController, str]]:
    controller = FixtureController()
    token = secrets.token_urlsafe(32)
    server = OwnerHttpServer(
        controller,
        SecretStr(token),
        session_limit=session_limit,
        studio_directory=studio_directory,
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server, controller, token
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
        assert not thread.is_alive()


def exchange(
    server: OwnerHttpServer,
    path: str,
    *,
    method: str = "GET",
    body: str | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, bytes, dict[str, str]]:
    connection = HTTPConnection("127.0.0.1", server.server_port, timeout=5)
    try:
        connection.request(
            method,
            path,
            body=body,
            headers={
                "Origin": server.origin,
                "Content-Type": "application/json",
                **(headers or {}),
            },
        )
        response = connection.getresponse()
        return response.status, response.read(), dict(response.getheaders())
    finally:
        connection.close()


def login(server: OwnerHttpServer, token: str) -> dict[str, str]:
    status, body, headers = exchange(
        server,
        "/api/production/session",
        method="POST",
        body="{}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert status == 200
    assert "HttpOnly" in headers["Set-Cookie"]
    assert "SameSite=Strict" in headers["Set-Cookie"]
    csrf = TypeAdapter(dict[str, str]).validate_json(body)["csrf"]
    return {"Cookie": headers["Set-Cookie"].split(";", 1)[0], "X-CSRF-Token": csrf}


def effect_request(*, revision: int = 0, action: str = "apply") -> str:
    return json.dumps(
        {
            "action": action,
            "epoch": "fixture-epoch",
            "revision": revision,
            "effect": {
                "capability": "graphics.pulse.v1",
                "preset": "rgb",
                "intensity_percent": 37,
                "duration_ms": 1000,
            },
        }
    )
