"""Synthetic provider-spec fixtures; no captured user accounts or credentials."""

import hmac
import json
from pathlib import Path
from typing import Final

from furbomek_gateway.production_sources.contracts import RatePolicy, SourcePolicy
from furbomek_gateway.production_sources.hyperliquid import HyperliquidPolicy
from furbomek_gateway.production_sources.twitch import TwitchPolicy

NOW: Final = 1795132800100
KEY: Final = bytes(range(32))
ACCOUNT: Final = "0x" + "1" * 40
RATE: Final = RatePolicy(
    source_per_minute=10, user_per_minute=2, load_evidence="synthetic-fixture-only"
)


def twitch_policy() -> TwitchPolicy:
    return TwitchPolicy(
        enabled=True,
        adapter_id="twitch-reader",
        scope="channel-one",
        session_id="session-one",
        rate=RATE,
        broadcaster_user_id="100",
        reader_user_id="200",
        subscription_id="sub-one",
    )


def liquidation_policy() -> HyperliquidPolicy:
    return HyperliquidPolicy(
        enabled=True,
        adapter_id="ledger-reader",
        scope="account-one",
        session_id="session-one",
        rate=RATE,
        account=ACCOUNT,
    )


def fixture(name: str) -> str:
    return (
        (Path(__file__).parent / "fixtures" / "production_sources" / name)
        .read_text()
        .replace(
            "SANITIZED_ACCOUNT",
            ACCOUNT,
        )
        .replace("SANITIZED_HASH", "0x" + "a" * 64)
    )


def signed(payload: str, policy: SourcePolicy, received_ms: int = NOW) -> bytes:
    values = [1, policy.adapter_id, policy.session_id, received_ms, payload]
    signature = hmac.digest(
        KEY,
        json.dumps(values, separators=(",", ":"), ensure_ascii=True).encode(),
        "sha256",
    ).hex()
    return json.dumps(
        {
            "schema_version": 1,
            "adapter_id": policy.adapter_id,
            "session_id": policy.session_id,
            "received_ms": received_ms,
            "payload": payload,
            "signature": signature,
        }
    ).encode()
