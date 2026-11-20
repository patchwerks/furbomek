"""Real collector state machines over a credential-free scripted wire transport."""

import json
from collections import deque
from typing import override

import pytest

from furbomek_gateway.production_sources import (
    HyperliquidAdapter,
    SourceDisposition,
    SourceReceipt,
    TwitchAdapter,
)
from furbomek_gateway.production_sources.auth import CollectorSigner
from furbomek_gateway.production_sources.contracts import SourceRejectedError
from furbomek_gateway.production_sources.sessions import (
    HyperliquidSession,
    Subscribe,
    TwitchAuthorization,
    TwitchSession,
    TwitchSubscription,
)

from .production_source_fixtures import (
    KEY,
    NOW,
    fixture,
    liquidation_policy,
    twitch_policy,
)


class Wire:
    """Scripted provider frames plus a subscription sink, without network access."""

    def __init__(self, peer: str, frames: list[bytes]) -> None:
        self.verified_peer_url: str = peer
        self.authorization: TwitchAuthorization = TwitchAuthorization(
            user_id="200", scopes=("user:read:chat",)
        )
        self.frames: deque[bytes] = deque(frames)
        self.subscriptions: list[Subscribe | TwitchSubscription] = []
        self.reconnects: list[str] = []

    def receive(self) -> bytes:
        return self.frames.popleft()

    def send_subscription(self, subscription: Subscribe) -> None:
        self.subscriptions.append(subscription)

    def subscribe_chat(self, subscription: TwitchSubscription) -> str:
        self.subscriptions.append(subscription)
        return "sub-one"

    def reconnect(self, url: str) -> None:
        self.reconnects.append(url)


def welcome(session_id: str = "session-one") -> bytes:
    return json.dumps(
        {
            "metadata": {
                "message_id": "welcome",
                "message_type": "session_welcome",
                "message_timestamp": "2026-11-20T00:00:00Z",
            },
            "payload": {
                "session": {
                    "id": session_id,
                    "status": "connected",
                    "reconnect_url": None,
                }
            },
        }
    ).encode()


def test_twitch_session_reconnect_never_repeats_ephemeral_request() -> None:
    policy = twitch_policy()
    reconnect = json.dumps(
        {
            "metadata": {
                "message_id": "reconnect",
                "message_type": "session_reconnect",
                "message_timestamp": "2026-11-20T00:00:00Z",
            },
            "payload": {
                "session": {
                    "id": "session-one",
                    "status": "reconnecting",
                    "reconnect_url": "wss://eventsub.wss.twitch.tv/ws?migration=synthetic",
                }
            },
        }
    ).encode()
    wire = Wire(
        "wss://eventsub.wss.twitch.tv/ws",
        [
            welcome(),
            fixture("twitch.json").encode(),
            reconnect,
            welcome("session-two"),
            fixture("twitch.json").replace("session-one", "session-two").encode(),
        ],
    )
    session = TwitchSession(
        TwitchAdapter(policy, KEY), wire, CollectorSigner(policy, KEY)
    )
    results = [session.poll(lambda: NOW) for _ in range(5)]
    assert [r.status for r in results] == [
        "observed",
        "accepted",
        "observed",
        "observed",
        "denied",
    ]
    assert results[-1] == SourceDisposition(status="denied", reason="duplicate")
    assert len(wire.subscriptions) == 1
    assert len(wire.reconnects) == 1


@pytest.mark.parametrize("invalid", ["peer", "reader", "scope"])
def test_twitch_session_denies_unenrolled_transport(invalid: str) -> None:
    policy = twitch_policy()
    wire = Wire("wss://eventsub.wss.twitch.tv/ws", [welcome()])
    if invalid == "peer":
        wire.verified_peer_url = "wss://attacker.invalid/ws"
    if invalid == "reader":
        wire.authorization = TwitchAuthorization(
            user_id="999", scopes=("user:read:chat",)
        )
    if invalid == "scope":
        wire.authorization = TwitchAuthorization(user_id="200", scopes=())
    session = TwitchSession(
        TwitchAdapter(policy, KEY), wire, CollectorSigner(policy, KEY)
    )
    with pytest.raises(SourceRejectedError, match="origin"):
        _ = session.poll(lambda: NOW)
    assert len(wire.frames) == 1
    assert wire.subscriptions == []


def test_liquidation_session_snapshot_replay_never_emits_cue() -> None:
    policy = liquidation_policy()
    wire = Wire(
        "wss://api.hyperliquid.xyz/ws",
        [
            fixture("liquidation.json")
            .replace('"isSnapshot":false', '"isSnapshot":true')
            .encode(),
            fixture("liquidation.json").encode(),
        ],
    )
    session = HyperliquidSession(
        HyperliquidAdapter(policy, KEY), wire, CollectorSigner(policy, KEY)
    )
    session.start()
    results = [session.poll(lambda: NOW) for _ in range(2)]
    assert results == [
        (SourceDisposition(status="observed", reason="snapshot"),),
        (SourceDisposition(status="denied", reason="duplicate"),),
    ]
    assert [s.model_dump()["method"] for s in wire.subscriptions] == [
        "subscribe",
        "subscribe",
    ]


def test_liquidation_session_delivers_typed_receipt() -> None:
    policy = liquidation_policy()
    wire = Wire("wss://api.hyperliquid.xyz/ws", [fixture("liquidation.json").encode()])
    session = HyperliquidSession(
        HyperliquidAdapter(policy, KEY), wire, CollectorSigner(policy, KEY)
    )
    session.start()
    results = session.poll(lambda: NOW)
    assert len(results) == 1
    assert isinstance(results[0], SourceReceipt)
    assert results[0].intent == "liquidation"


def test_liquidation_poll_samples_host_time_after_receive() -> None:
    current_ms = NOW - 20000

    class DelayedWire(Wire):
        @override
        def receive(self) -> bytes:
            nonlocal current_ms
            current_ms = NOW
            return super().receive()

    policy = liquidation_policy()
    wire = DelayedWire(
        "wss://api.hyperliquid.xyz/ws", [fixture("liquidation.json").encode()]
    )
    session = HyperliquidSession(
        HyperliquidAdapter(policy, KEY), wire, CollectorSigner(policy, KEY)
    )
    results = session.poll(lambda: current_ms)
    assert isinstance(results[0], SourceReceipt)
    assert results[0].event.received_ms == NOW
