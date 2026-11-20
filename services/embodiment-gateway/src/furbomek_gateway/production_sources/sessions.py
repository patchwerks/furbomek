"""Read-only sessions using injected authorized provider transports."""

import json
from collections.abc import Callable
from typing import Literal, Protocol, assert_never
from urllib.parse import urlsplit

from furbomek_gateway.effect_contracts import Contract, Identifier

from .auth import CollectorSigner, parse
from .contracts import SourceDisposition, SourceResult, reject
from .hyperliquid import Account, HyperliquidAdapter
from .twitch import TwitchAdapter
from .twitch_models import Condition, Frame, ProviderModel, Transport


class TwitchSubscription(Contract):
    """Exact EventSub chat-read subscription body for the OAuth transport."""

    type: Literal["channel.chat.message"] = "channel.chat.message"
    version: Literal["1"] = "1"
    condition: Condition
    transport: Transport


class UserSubscription(Contract):
    """Read-only Hyperliquid subscription; no exchange/order channel exists."""

    type: Literal["userEvents", "userNonFundingLedgerUpdates"]
    user: Account


class Subscribe(Contract):
    """Exact Hyperliquid websocket request."""

    method: Literal["subscribe"] = "subscribe"
    subscription: UserSubscription


class WebSocketTransport(Protocol):
    """Owner provides TLS hostname verification, bounded reads and cancellation.

    Implementations must reject unverified TLS, redirects and unsolicited peers.
    The interface owns no robot, order, shell or public-chat operation.
    """

    @property
    def verified_peer_url(self) -> str:
        """Return the actual TLS-verified peer URL, never a payload-supplied claim."""
        ...

    def receive(self) -> bytes:
        """Read one bounded provider websocket text frame or raise on disconnect."""
        ...

    def send_subscription(self, subscription: Subscribe) -> None:
        """Send only a typed read-only subscription."""
        ...


class TwitchAuthorization(Contract):
    """Validated OAuth identity returned by the private transport enrollment."""

    user_id: Identifier
    scopes: tuple[Literal["user:read:chat"], ...]


class TwitchTransport(WebSocketTransport, Protocol):
    """OAuth transport is enrolled for this reader's user:read:chat scope only."""

    @property
    def authorization(self) -> TwitchAuthorization:
        """Return token-validation identity; never infer it from event data."""
        ...

    def subscribe_chat(self, subscription: TwitchSubscription) -> Identifier:
        """Create EventSub read subscription; return its actual provider ID."""
        ...

    def reconnect(self, url: str) -> None:
        """Follow verified Twitch reconnect; retain old socket until welcome."""
        ...


class Session(ProviderModel):
    """Welcome and reconnect transport metadata."""

    id: Identifier
    status: Literal["connected", "reconnecting"]
    reconnect_url: str | None = None


class SessionPayload(ProviderModel):
    """Transport-only payload, never an event."""

    session: Session


def require_peer(url: str, host: str) -> None:
    """Forbid redirects, userinfo, ports, fragments and alternate origins."""
    parts = urlsplit(url)
    if (
        parts.scheme != "wss"
        or parts.hostname != host
        or parts.username
        or parts.password
        or parts.port
        or parts.fragment
    ):
        reject("origin")


class TwitchSession:
    """Enrolled EventSub collector; reconnect keeps adapter dedupe and rate state."""

    def __init__(
        self,
        adapter: TwitchAdapter,
        transport: TwitchTransport,
        signer: CollectorSigner,
    ) -> None:
        """Connect one trusted source signer to one injected TLS/OAuth transport."""
        self.adapter: TwitchAdapter = adapter
        self.transport: TwitchTransport = transport
        self.signer: CollectorSigner = signer
        self._subscribed: bool = False

    def poll(self, clock: Callable[[], int]) -> SourceResult:
        """Process one real transport frame; welcome/reconnect never emit cues."""
        if not self.adapter.policy.enabled:
            return SourceDisposition(status="denied", reason="disabled")
        require_peer(self.transport.verified_peer_url, "eventsub.wss.twitch.tv")
        authorization = self.transport.authorization
        if (
            authorization.user_id != self.adapter.policy.reader_user_id
            or "user:read:chat" not in authorization.scopes
        ):
            reject("origin")
        try:
            raw = self.transport.receive()
        except ConnectionError:
            self._subscribed = False
            raise
        frame = parse(Frame, raw)
        match frame.metadata.message_type:
            case "session_welcome":
                session = parse(
                    SessionPayload, json.dumps(frame.payload).encode()
                ).session
                if session.status != "connected" or session.reconnect_url is not None:
                    reject("malformed")
                self._welcome(session.id)
                return SourceDisposition(status="observed", reason="control")
            case "session_reconnect":
                session = parse(
                    SessionPayload, json.dumps(frame.payload).encode()
                ).session
                if (
                    session.status != "reconnecting"
                    or session.reconnect_url is None
                    or session.id != self.adapter.auth.session_id
                ):
                    reject("origin")
                require_peer(session.reconnect_url, "eventsub.wss.twitch.tv")
                self.transport.reconnect(session.reconnect_url)
                return SourceDisposition(status="observed", reason="control")
            case "notification" | "session_keepalive" | "revocation":
                now_ms = clock()
                return self.adapter.receive(self.signer.seal(raw, now_ms), now_ms)
            case _:
                assert_never(frame.metadata.message_type)

    def _welcome(self, session_id: str) -> None:
        """Bind a fresh verified socket; ordinary migration retains subscriptions."""
        self.adapter.reconnect(session_id)
        self.signer.policy = self.signer.policy.model_copy(
            update={"session_id": session_id}
        )
        if not self._subscribed:
            request = TwitchSubscription(
                condition=Condition(
                    broadcaster_user_id=self.adapter.policy.broadcaster_user_id,
                    user_id=self.adapter.policy.reader_user_id,
                ),
                transport=Transport(method="websocket", session_id=session_id),
            )
            subscription_id = self.transport.subscribe_chat(request)
            self.adapter.policy = self.adapter.policy.model_copy(
                update={"subscription_id": subscription_id}
            )
            self._subscribed = True


class HyperliquidSession:
    """Subscribe only to authorized account observations; never signing or orders."""

    def __init__(
        self,
        adapter: HyperliquidAdapter,
        transport: WebSocketTransport,
        signer: CollectorSigner,
    ) -> None:
        """Bind the account adapter to an owner-provided verified websocket."""
        self.adapter: HyperliquidAdapter = adapter
        self.transport: WebSocketTransport = transport
        self.signer: CollectorSigner = signer

    def start(self) -> None:
        """Subscribe on a fresh/reconnected TLS socket; snapshots stay inert."""
        if not self.adapter.policy.enabled:
            reject("disabled")
        require_peer(self.transport.verified_peer_url, "api.hyperliquid.xyz")
        self.transport.send_subscription(
            Subscribe(
                subscription=UserSubscription(
                    type="userEvents", user=self.adapter.policy.account
                )
            )
        )
        self.transport.send_subscription(
            Subscribe(
                subscription=UserSubscription(
                    type="userNonFundingLedgerUpdates", user=self.adapter.policy.account
                )
            )
        )

    def poll(self, clock: Callable[[], int]) -> tuple[SourceResult, ...]:
        """Read one verified frame and normalize through authenticated ingress."""
        if not self.adapter.policy.enabled:
            return (SourceDisposition(status="denied", reason="disabled"),)
        require_peer(self.transport.verified_peer_url, "api.hyperliquid.xyz")
        raw = self.transport.receive()
        now_ms = clock()
        return self.adapter.receive(self.signer.seal(raw, now_ms), now_ms)
