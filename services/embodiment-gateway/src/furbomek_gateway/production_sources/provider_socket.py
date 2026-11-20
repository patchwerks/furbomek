"""Pinned TLS WebSocket transport; only typed provider-read requests are exposed."""

import ssl
from collections.abc import Generator
from contextlib import ExitStack, contextmanager
from typing import Literal, assert_never

from websockets.exceptions import ConnectionClosed
from websockets.sync.client import ClientConnection, connect

from furbomek_gateway.effect_contracts import Identifier

from .auth import MAX_BYTES, parse
from .contracts import reject
from .provider_http import TwitchApi, require_tls
from .sessions import Subscribe, TwitchAuthorization, TwitchSubscription, require_peer
from .twitch_models import Frame


class ProviderSocket:
    """Context-owned connections; old Twitch socket stays until replacement welcome."""

    def __init__(
        self,
        source: Literal["twitch", "hyperliquid"],
        tls: ssl.SSLContext | None = None,
    ) -> None:
        """Choose fixed production endpoint without opening a socket."""
        self.tls: ssl.SSLContext = tls or ssl.create_default_context()
        require_tls(self.tls)
        self.source: Literal["twitch", "hyperliquid"] = source
        self.verified_peer_url: str = ""
        self._connection: ClientConnection | None = None
        self._retiring: ClientConnection | None = None
        self._stack: ExitStack = ExitStack()

    @contextmanager
    def opened(self) -> Generator["ProviderSocket"]:
        """Open explicit fixed peer with bounded handshake, receive and close."""
        match self.source:
            case "twitch":
                url = "wss://eventsub.wss.twitch.tv/ws?keepalive_timeout_seconds=10"
            case "hyperliquid":
                url = "wss://api.hyperliquid.xyz/ws"
            case _:
                assert_never(self.source)
        with self._stack:
            self._connection = self._connect(url)
            try:
                yield self
            finally:
                self._connection = None
                self._retiring = None
                self.verified_peer_url = ""

    def _connect(self, url: str) -> ClientConnection:
        """Sync websockets rejects redirects; disable proxies and bounded buffers."""
        require_tls(self.tls)
        connection = connect(
            url,
            ssl=self.tls,
            proxy=None,
            open_timeout=5,
            close_timeout=1,
            max_size=MAX_BYTES,
            max_queue=4,
            compression=None,
            ping_interval=5,
            ping_timeout=5,
        )
        _ = self._stack.enter_context(connection)
        self.verified_peer_url = url
        return connection

    def receive(self) -> bytes:
        """Timeout/disconnect is explicit; binary frames never become trusted JSON."""
        if self._connection is None:
            reject("origin")
        try:
            raw = self._connection.recv(timeout=10)
        except (ConnectionClosed, TimeoutError) as exc:
            msg = "provider disconnected"
            raise ConnectionError(msg) from exc
        match raw:
            case str():
                payload = raw.encode()
            case bytes():
                reject("malformed")
            case _:
                assert_never(raw)
        if self._retiring is not None:
            frame = parse(Frame, payload)
            if frame.metadata.message_type != "session_welcome":
                reject("origin")
            self._retiring.close()
            self._retiring = None
        return payload

    def send_subscription(self, subscription: Subscribe) -> None:
        """Only typed Hyperliquid read subscriptions may be written to the socket."""
        if self.source != "hyperliquid" or self._connection is None:
            reject("origin")
        self._connection.send(subscription.model_dump_json())

    def reconnect(self, url: str) -> None:
        """Migrate only to Twitch's verified hostname, retaining one old socket."""
        if self.source != "twitch" or self._connection is None or self._retiring:
            reject("origin")
        require_peer(url, "eventsub.wss.twitch.tv")
        replacement = self._connect(url)
        self._retiring = self._connection
        self._connection = replacement


class TwitchSocket:
    """Compose the TLS websocket with the explicit private OAuth HTTP client."""

    def __init__(self, socket: ProviderSocket, api: TwitchApi) -> None:
        """Take already context-owned transport and explicit credential client."""
        if socket.source != "twitch":
            reject("origin")
        self.socket: ProviderSocket = socket
        self.api: TwitchApi = api

    @property
    def verified_peer_url(self) -> str:
        """Return the actual opened socket's verified endpoint."""
        return self.socket.verified_peer_url

    @property
    def authorization(self) -> TwitchAuthorization:
        """Independently revalidate the configured reader token before ingress."""
        return self.api.validate()

    def receive(self) -> bytes:
        """Receive one bounded provider text frame."""
        return self.socket.receive()

    def send_subscription(self, _subscription: Subscribe) -> None:
        """Twitch has no Hyperliquid subscription operation."""
        reject("origin")

    def subscribe_chat(self, subscription: TwitchSubscription) -> Identifier:
        """Send only the typed EventSub chat-read subscription."""
        return self.api.subscribe(subscription)

    def reconnect(self, url: str) -> None:
        """Use the same TLS authority checks as initial connection."""
        self.socket.reconnect(url)
