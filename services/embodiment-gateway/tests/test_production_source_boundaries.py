"""Ingress fail-closed state, receipt identities and private authority boundaries."""

import json

from furbomek_gateway.production_sources import (
    HyperliquidAdapter,
    SourceDisposition,
    SourceReceipt,
    TwitchAdapter,
)

from .production_source_fixtures import (
    KEY,
    NOW,
    fixture,
    liquidation_policy,
    signed,
    twitch_policy,
)


def test_twitch_revocation_latches_until_operator_reenrollment() -> None:
    policy = twitch_policy()
    adapter = TwitchAdapter(policy, KEY)
    revocation = json.dumps(
        {
            "metadata": {
                "message_id": "revoked",
                "message_type": "revocation",
                "message_timestamp": "2026-11-20T00:00:00Z",
            },
            "payload": {},
        }
    )
    _ = adapter.receive(signed(revocation, policy), NOW)
    adapter.reconnect("session-two")
    policy = policy.model_copy(update={"session_id": "session-two"})
    result = adapter.receive(signed(fixture("twitch.json"), policy), NOW)
    assert result == SourceDisposition(status="denied", reason="revoked")


def test_twitch_disabled_policy_denies_even_authenticated_delivery() -> None:
    policy = twitch_policy().model_copy(update={"enabled": False})
    result = TwitchAdapter(policy, KEY).receive(
        signed(fixture("twitch.json"), policy), NOW
    )
    assert result == SourceDisposition(status="denied", reason="disabled")


def test_liquidation_origin_cannot_reuse_twitch_delivery_identity() -> None:
    result = HyperliquidAdapter(liquidation_policy(), KEY).receive(
        signed(fixture("liquidation.json"), twitch_policy()), NOW
    )
    assert result == (SourceDisposition(status="denied", reason="origin"),)


def test_twitch_restart_keeps_durable_identity_despite_new_transport() -> None:
    policy = twitch_policy()
    first = TwitchAdapter(policy, KEY).receive(
        signed(fixture("twitch.json"), policy), NOW
    )
    policy = policy.model_copy(update={"session_id": "session-two"})
    payload = (
        fixture("twitch.json")
        .replace("session-one", "session-two")
        .replace("delivery-one", "delivery-two")
    )
    second = TwitchAdapter(policy, KEY).receive(signed(payload, policy), NOW)
    assert isinstance(first, SourceReceipt)
    assert isinstance(second, SourceReceipt)
    assert second.event.dedupe_key == first.event.dedupe_key


def test_liquidation_duplicate_in_same_batch_yields_one_receipt() -> None:
    policy = liquidation_policy()
    payload = fixture("liquidation.json")
    entry_start = payload.index('{"time":')
    entry_end = payload.rindex("]}}")
    payload = (
        payload[:entry_end] + "," + payload[entry_start:entry_end] + payload[entry_end:]
    )
    results = HyperliquidAdapter(policy, KEY).receive(signed(payload, policy), NOW)
    assert len(results) == 2
    assert isinstance(results[0], SourceReceipt)
    assert results[1] == SourceDisposition(status="denied", reason="duplicate")


def test_twitch_delayed_receipt_cannot_be_resigned_into_freshness() -> None:
    policy = twitch_policy()
    result = TwitchAdapter(policy, KEY).receive(
        signed(fixture("twitch.json"), policy), NOW + 1001
    )
    assert result == SourceDisposition(status="denied", reason="stale")


def test_twitch_deeply_nested_provider_input_is_redacted_denial() -> None:
    policy = twitch_policy()
    payload = "[" * 10000 + "0" + "]" * 10000
    result = TwitchAdapter(policy, KEY).receive(signed(payload, policy), NOW)
    assert result == SourceDisposition(status="denied", reason="malformed")
