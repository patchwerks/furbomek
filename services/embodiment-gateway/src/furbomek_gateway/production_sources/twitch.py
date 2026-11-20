"""Authenticated EventSub ingress restricted to curated audience intents."""

import json
from datetime import datetime
from typing import Final, assert_never

from pydantic import ValidationError

from furbomek_gateway.effect_contracts import Identifier
from furbomek_gateway.reaction_contracts import PrivateEvent

from .auth import Authenticator, Delivery, parse, private_id
from .contracts import (
    Intent,
    SourceDisposition,
    SourcePolicy,
    SourceReceipt,
    SourceRejectedError,
    SourceResult,
    reject,
)
from .gate import EventGate
from .twitch_models import Frame, Notification

INTENTS: Final[dict[str, Intent]] = {
    "!ack": "acknowledge",
    "!rgb": "rgb",
    "!xyz": "xyz",
}


class TwitchPolicy(SourcePolicy):
    """Operator-approved chat reader, subscription and moderation blocklist."""

    broadcaster_user_id: Identifier
    reader_user_id: Identifier
    subscription_id: Identifier
    blocked_users: tuple[Identifier, ...] = ()
    blocked_messages: tuple[Identifier, ...] = ()


class TwitchAdapter:
    """Mutable session/revocation state; no provider writes or tool execution."""

    def __init__(self, policy: TwitchPolicy, key: bytes) -> None:
        """Bind operator policy to one authenticated source."""
        self.policy: TwitchPolicy = policy
        self.auth: Authenticator = Authenticator(policy, key)
        self.gate: EventGate = EventGate(policy)
        self._revoked: bool = False

    def reconnect(self, session_id: Identifier) -> None:
        """Trusted collector rebinds a verified session without clearing dedupe."""
        self.auth.session_id = session_id

    def receive(self, raw: bytes, now_ms: int) -> SourceResult:
        """Normalize authenticated provider data; all denials are redacted."""
        try:
            delivery = self.auth.verify(raw, now_ms)
            if self._revoked:
                reject("revoked")
            return self._normalize(delivery, now_ms)
        except SourceRejectedError as exc:
            return SourceDisposition(status="denied", reason=exc.reason)
        except (ValidationError, ValueError, UnicodeError, OverflowError):
            return SourceDisposition(status="denied", reason="malformed")

    def _normalize(self, delivery: Delivery, now_ms: int) -> SourceResult:
        """Convert one verified delivery into bounded source outcomes."""
        frame = parse(Frame, delivery.payload.encode())
        match frame.metadata.message_type:
            case "session_welcome" | "session_keepalive" | "session_reconnect":
                return SourceDisposition(status="observed", reason="control")
            case "revocation":
                self._revoked = True
                return SourceDisposition(status="observed", reason="revoked")
            case "notification":
                pass
            case _:
                assert_never(frame.metadata.message_type)
        if (
            frame.metadata.subscription_type != "channel.chat.message"
            or frame.metadata.subscription_version != "1"
        ):
            reject("scope")
        payload = parse(Notification, json.dumps(frame.payload).encode())
        subscription, chat = payload.subscription, payload.event
        if (
            subscription.id != self.policy.subscription_id
            or subscription.condition.broadcaster_user_id
            != self.policy.broadcaster_user_id
            or subscription.condition.user_id != self.policy.reader_user_id
            or subscription.transport.session_id != delivery.session_id
            or chat.broadcaster_user_id != self.policy.broadcaster_user_id
            or chat.source_broadcaster_user_id
            not in (None, self.policy.broadcaster_user_id)
        ):
            reject("scope")
        if (
            chat.chatter_user_id in self.policy.blocked_users
            or chat.message_id in self.policy.blocked_messages
        ):
            reject("moderation")
        intent = INTENTS.get(chat.message.text)
        if intent is None:
            reject("intent")
        timestamp = datetime.fromisoformat(frame.metadata.message_timestamp)
        if timestamp.tzinfo is None:
            reject("malformed")
        occurred_ms = int(timestamp.timestamp() * 1000)
        if not occurred_ms <= now_ms <= occurred_ms + self.policy.max_age_ms:
            reject("stale")
        event = PrivateEvent(
            source="twitch.eventsub.v1",
            scope=self.policy.scope,
            stable_id=private_id(chat.message_id),
            causation_id=private_id(chat.message_id),
            origin="adapter",
            occurred_ms=occurred_ms,
            received_ms=delivery.received_ms,
            max_age_ms=self.policy.max_age_ms,
        )
        self.gate.admit(event, private_id(chat.chatter_user_id))
        return SourceReceipt(
            event=event, intent=intent, preview="Audience preset requested"
        )
