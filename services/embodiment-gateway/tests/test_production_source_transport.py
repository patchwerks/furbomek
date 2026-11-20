"""Real TLS websocket/HTTP client tests using only owned loopback servers."""

import json
import ssl
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import override

import pytest
from pydantic import SecretStr, TypeAdapter
from websockets.exceptions import ConnectionClosed
from websockets.sync.server import ServerConnection, serve

from furbomek_gateway.production_sources import HyperliquidAdapter, SourceReceipt
from furbomek_gateway.production_sources.auth import CollectorSigner
from furbomek_gateway.production_sources.contracts import SourceRejectedError
from furbomek_gateway.production_sources.provider_http import (
    TwitchApi,
    TwitchCredentials,
)
from furbomek_gateway.production_sources.provider_socket import ProviderSocket
from furbomek_gateway.production_sources.sessions import (
    HyperliquidSession,
    TwitchSubscription,
)
from furbomek_gateway.production_sources.twitch_models import Condition, Transport

from .production_source_fixtures import KEY, NOW, fixture, liquidation_policy
from .production_tls_fixture import contexts, route_loopback
from .test_production_source_sessions import welcome


def test_liquidation_concrete_tls_transport_delivers_redacted_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tls = contexts(tmp_path)
    subscriptions: list[str | bytes] = []

    def handler(connection: ServerConnection) -> None:
        subscriptions.extend([connection.recv(timeout=2), connection.recv(timeout=2)])
        connection.send(fixture("liquidation.json"))

    with serve(handler, "127.0.0.1", 0, ssl=tls.server) as server:
        route_loopback(
            monkeypatch,
            TypeAdapter(tuple[str, int]).validate_python(server.socket.getsockname())[
                1
            ],
        )
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            with ProviderSocket("hyperliquid", tls.client).opened() as transport:
                policy = liquidation_policy()
                session = HyperliquidSession(
                    HyperliquidAdapter(policy, KEY),
                    transport,
                    CollectorSigner(policy, KEY),
                )
                session.start()
                results = session.poll(lambda: NOW)
        finally:
            server.shutdown()
            thread.join(timeout=3)
    assert len(results) == 1
    assert isinstance(results[0], SourceReceipt)
    assert results[0].intent == "liquidation"
    assert len(subscriptions) == 2


def test_tls_transport_refuses_disabled_certificate_validation() -> None:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    with pytest.raises(SourceRejectedError, match="origin"):
        _ = ProviderSocket("twitch", context)


@pytest.mark.parametrize(
    ("status", "reader"), [(202, "200"), (302, "200"), (401, "200"), (202, "999")]
)
def test_twitch_concrete_https_subscription_validates_response(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, status: int, reader: str
) -> None:
    tls = contexts(tmp_path)
    observed: list[str] = []
    response = {
        "data": [
            {
                "id": "sub-one",
                "status": "enabled",
                "type": "channel.chat.message",
                "version": "1",
                "condition": {"broadcaster_user_id": "100", "user_id": "200"},
                "transport": {"method": "websocket", "session_id": "session-one"},
            }
        ]
    }

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            observed.append(self.path)
            self.send_response(200)
            self.end_headers()
            _ = self.wfile.write(
                json.dumps(
                    {
                        "client_id": "fixture-client",
                        "user_id": reader,
                        "scopes": ["user:read:chat"],
                        "expires_in": 3600,
                    }
                ).encode()
            )

        def do_POST(self) -> None:
            observed.append(self.path)
            _ = self.rfile.read(int(self.headers["Content-Length"]))
            self.send_response(status)
            self.send_header("Location", "https://attacker.invalid/")
            self.end_headers()
            _ = self.wfile.write(json.dumps(response).encode())

        @override
        def log_message(self, format: str, *args: str) -> None:
            """Keep synthetic authentication request data out of test output."""

    with HTTPServer(("127.0.0.1", 0), Handler) as server:
        server.socket = tls.server.wrap_socket(server.socket, server_side=True)
        route_loopback(monkeypatch, server.server_port)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            api = TwitchApi(
                TwitchCredentials(
                    client_id="fixture-client",
                    token=SecretStr("synthetic-token"),
                    reader_user_id="200",
                    broadcaster_user_id="100",
                ),
                tls.client,
            )
            request = TwitchSubscription(
                condition=Condition(broadcaster_user_id="100", user_id="200"),
                transport=Transport(method="websocket", session_id="session-one"),
            )
            if status == 202 and reader == "200":
                assert api.subscribe(request) == "sub-one"
            else:
                with pytest.raises(SourceRejectedError, match="origin"):
                    _ = api.subscribe(request)
        finally:
            server.shutdown()
            thread.join(timeout=3)
    assert observed == (
        ["/oauth2/validate", "/helix/eventsub/subscriptions"]
        if reader == "200"
        else ["/oauth2/validate"]
    )


def test_twitch_concrete_tls_reconnect_holds_old_socket_until_welcome(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tls = contexts(tmp_path)
    closed = threading.Event()
    arrivals: list[ServerConnection] = []

    def handler(connection: ServerConnection) -> None:
        arrivals.append(connection)
        connection.send(welcome().decode())
        if len(arrivals) == 1:
            try:
                _ = connection.recv(timeout=3)
            except ConnectionClosed:
                closed.set()

    with serve(handler, "127.0.0.1", 0, ssl=tls.server) as server:
        route_loopback(
            monkeypatch,
            TypeAdapter(tuple[str, int]).validate_python(server.socket.getsockname())[
                1
            ],
        )
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            with ProviderSocket("twitch", tls.client).opened() as transport:
                _ = transport.receive()
                transport.reconnect("wss://eventsub.wss.twitch.tv/ws?migration=fixture")
                assert not closed.is_set()
                assert transport.receive() == welcome()
                assert closed.wait(timeout=2)
        finally:
            server.shutdown()
            thread.join(timeout=3)


def test_concrete_tls_rejects_untrusted_certificate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tls = contexts(tmp_path)
    received = threading.Event()

    def handler(_connection: ServerConnection) -> None:
        received.set()

    with serve(handler, "127.0.0.1", 0, ssl=tls.server) as server:
        route_loopback(
            monkeypatch,
            TypeAdapter(tuple[str, int]).validate_python(server.socket.getsockname())[
                1
            ],
        )
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            with (
                pytest.raises(ssl.SSLCertVerificationError),
                ProviderSocket("hyperliquid").opened(),
            ):
                pytest.fail("untrusted TLS must not open")
        finally:
            server.shutdown()
            thread.join(timeout=3)
    assert not received.is_set()
