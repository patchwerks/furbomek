"""Authenticate collector deliveries, independently of provider JSON claims."""

import hashlib
import hmac
import json
from typing import Annotated, Final

from pydantic import Field

from furbomek_gateway.effect_contracts import Contract, Identifier
from furbomek_gateway.reaction_contracts import unique_keys

from .contracts import SourcePolicy, reject

MAX_BYTES: Final = 65536
KEY_BYTES: Final = 32


class Delivery(Contract):
    """Locally signed collector envelope; not a provider signature format."""

    schema_version: Annotated[int, Field(ge=1, le=1)] = 1
    adapter_id: Identifier
    session_id: Identifier
    received_ms: Annotated[int, Field(ge=0)]
    payload: Annotated[str, Field(max_length=32768)]
    signature: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]

    def signing_bytes(self) -> bytes:
        """Canonical UTF-8 encoding binds body, origin, session and receipt time."""
        return json.dumps(
            [
                self.schema_version,
                self.adapter_id,
                self.session_id,
                self.received_ms,
                self.payload,
            ],
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode()


def parse[T: Contract](model: type[T], raw: bytes) -> T:
    """Reject oversized input and duplicate keys before typed JSON parsing."""
    if len(raw) > MAX_BYTES:
        reject("malformed")
    try:
        json.loads(raw.decode(), object_pairs_hook=unique_keys)
    except RecursionError:
        reject("malformed")
    return model.model_validate_json(raw)


class Authenticator:
    """Private, per-source key verifier; transport enrollment is out of band."""

    def __init__(self, policy: SourcePolicy, key: bytes) -> None:
        """Retain private key material only in this process."""
        if len(key) < KEY_BYTES:
            reject("origin")
        self.policy: SourcePolicy = policy
        self._key: bytes = key
        self.session_id: str = policy.session_id

    def verify(self, raw: bytes, now_ms: int) -> Delivery:
        """Verify local provenance before interpreting provider payload."""
        if not self.policy.enabled:
            reject("disabled")
        delivery = parse(Delivery, raw)
        expected = hmac.digest(self._key, delivery.signing_bytes(), "sha256").hex()
        if (
            not hmac.compare_digest(expected, delivery.signature)
            or delivery.adapter_id != self.policy.adapter_id
            or delivery.session_id != self.session_id
        ):
            reject("origin")
        if not delivery.received_ms <= now_ms <= delivery.received_ms + 1000:
            reject("stale")
        return delivery


def private_id(value: str) -> str:
    """Stable opaque digest; never send provider IDs or addresses to renderers."""
    return hashlib.sha256(value.encode()).hexdigest()


class CollectorSigner:
    """Source-scoped local delivery signer for an enrolled trusted collector."""

    def __init__(self, policy: SourcePolicy, key: bytes) -> None:
        """Retain a separate per-source key, never a provider credential."""
        if len(key) < KEY_BYTES:
            reject("origin")
        self.policy: SourcePolicy = policy
        self._key: bytes = key

    def seal(self, payload: bytes, received_ms: int) -> bytes:
        """Sign provider bytes only after the collector verifies its transport."""
        unsigned = Delivery(
            adapter_id=self.policy.adapter_id,
            session_id=self.policy.session_id,
            received_ms=received_ms,
            payload=payload.decode(),
            signature="0" * 64,
        )
        signature = hmac.digest(self._key, unsigned.signing_bytes(), "sha256").hex()
        return (
            unsigned.model_copy(update={"signature": signature})
            .model_dump_json()
            .encode()
        )
