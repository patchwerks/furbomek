"""Read-only liquidation ingress; timestamped ledger is the reaction authority."""

import json
from typing import Annotated, Literal, assert_never

from pydantic import Field, JsonValue, ValidationError

from furbomek_gateway.effect_contracts import Identifier
from furbomek_gateway.reaction_contracts import PrivateEvent

from .auth import Authenticator, Delivery, parse, private_id
from .contracts import (
    SourceDisposition,
    SourcePolicy,
    SourceReceipt,
    SourceRejectedError,
    SourceResult,
    reject,
)
from .gate import EventGate
from .twitch_models import ProviderModel

Account = Annotated[str, Field(pattern=r"^0x[0-9a-fA-F]{40}$")]


class HyperliquidPolicy(SourcePolicy):
    """Account is private operator configuration, never a signing credential."""

    account: Account

    def require_account(self, account: str) -> None:
        """Verify the expected account on every account-bearing message."""
        if account.lower() != self.account.lower():
            reject("scope")


class Liquidation(ProviderModel):
    """Immediate liquidation lacks a documented occurrence timestamp."""

    lid: Annotated[int, Field(ge=0)]
    liquidated_user: Account


class Immediate(ProviderModel):
    """Untimed notifications cannot establish reaction freshness."""

    liquidation: Liquidation


class Delta(ProviderModel):
    """Only provider-typed liquidation deltas are relevant."""

    type: Literal["liquidation"]


class LedgerEntry(ProviderModel):
    """Provider hash plus time define an account-scoped stable ledger event."""

    time: Annotated[int, Field(ge=0)]
    hash: Annotated[str, Field(pattern=r"^0x[0-9a-fA-F]{64}$")]
    delta: Delta


class Ledger(ProviderModel):
    """Snapshot is required explicitly; omission cannot turn history into live."""

    user: Account
    isSnapshot: bool  # noqa: N815 -- exact provider field
    nonFundingLedgerUpdates: Annotated[  # noqa: N815 -- exact provider field
        tuple[JsonValue, ...], Field(max_length=100)
    ]


class Frame(ProviderModel):
    """Closed relevant subscription channels; unrelated events are denied."""

    channel: Literal["user", "userNonFundingLedgerUpdates", "subscriptionResponse"]
    data: JsonValue


class HyperliquidAdapter:
    """Mutable in-process rates/dedupe; durable reservation remains downstream."""

    def __init__(self, policy: HyperliquidPolicy, key: bytes) -> None:
        """Bind operator policy to one authenticated source."""
        self.policy: HyperliquidPolicy = policy
        self.auth: Authenticator = Authenticator(policy, key)
        self.gate: EventGate = EventGate(policy)

    def reconnect(self, session_id: Identifier) -> None:
        """Rebind trusted transport while retaining recent event identities."""
        self.auth.session_id = session_id

    def receive(self, raw: bytes, now_ms: int) -> tuple[SourceResult, ...]:
        """Emit only fresh account-bound ledger liquidations, never snapshots."""
        try:
            delivery = self.auth.verify(raw, now_ms)
            return self._normalize(delivery, now_ms)
        except SourceRejectedError as exc:
            return (SourceDisposition(status="denied", reason=exc.reason),)
        except (ValidationError, ValueError, UnicodeError):
            return (SourceDisposition(status="denied", reason="malformed"),)

    def _normalize(self, delivery: Delivery, now_ms: int) -> tuple[SourceResult, ...]:
        """Convert one verified delivery into bounded source outcomes."""
        frame = parse(Frame, delivery.payload.encode())
        match frame.channel:
            case "subscriptionResponse":
                return (SourceDisposition(status="observed", reason="control"),)
            case "user":
                immediate = parse(Immediate, json.dumps(frame.data).encode())
                self.policy.require_account(immediate.liquidation.liquidated_user)
                return (SourceDisposition(status="observed", reason="untimed"),)
            case "userNonFundingLedgerUpdates":
                ledger = parse(Ledger, json.dumps(frame.data).encode())
            case _:
                assert_never(frame.channel)
        self.policy.require_account(ledger.user)
        if ledger.isSnapshot:
            self._remember_snapshot(ledger, now_ms)
            return (SourceDisposition(status="observed", reason="snapshot"),)
        results: list[SourceResult] = []
        for raw_entry in ledger.nonFundingLedgerUpdates:
            try:
                entry = parse(LedgerEntry, json.dumps(raw_entry).encode())
                if not entry.time <= now_ms <= entry.time + self.policy.max_age_ms:
                    reject("stale")
                identity = private_id(entry.hash.lower())
                event = PrivateEvent(
                    source="hyperliquid.ledger.v1",
                    scope=self.policy.scope,
                    stable_id=identity,
                    causation_id=identity,
                    origin="adapter",
                    occurred_ms=entry.time,
                    received_ms=delivery.received_ms,
                    max_age_ms=self.policy.max_age_ms,
                )
                self.gate.admit(event, self.policy.scope)
                results.append(
                    SourceReceipt(
                        event=event,
                        intent="liquidation",
                        preview="Liquidation observed",
                    )
                )
            except SourceRejectedError as exc:
                results.append(SourceDisposition(status="denied", reason=exc.reason))
            except (ValidationError, ValueError):
                results.append(SourceDisposition(status="denied", reason="malformed"))
        return tuple(results)

    def _remember_snapshot(self, ledger: Ledger, now_ms: int) -> None:
        """Remember fresh snapshot identities without authorizing their reactions."""
        for raw in ledger.nonFundingLedgerUpdates:
            try:
                entry = parse(LedgerEntry, json.dumps(raw).encode())
            except (ValidationError, ValueError):
                continue
            if entry.time <= now_ms <= entry.time + self.policy.max_age_ms:
                self.gate.observe(private_id(entry.hash.lower()), now_ms)
