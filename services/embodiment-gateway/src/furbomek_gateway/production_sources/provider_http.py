"""Fixed-destination Twitch token validation and EventSub read subscription HTTP."""

import ssl
import time
from typing import Annotated, Literal

import httpx
from pydantic import Field, SecretStr

from furbomek_gateway.effect_contracts import Contract, Identifier

from .auth import MAX_BYTES, parse
from .contracts import reject
from .sessions import TwitchAuthorization, TwitchSubscription
from .twitch_models import Condition, ProviderModel, Transport


class TwitchCredentials(Contract):
    """Explicit private runtime input; never read ambient environment credentials."""

    client_id: Identifier
    token: SecretStr
    reader_user_id: Identifier
    broadcaster_user_id: Identifier


class TokenIdentity(ProviderModel):
    """Actual OAuth validation response, including expiration and granted scopes."""

    client_id: Identifier
    user_id: Identifier
    scopes: tuple[str, ...]
    expires_in: Annotated[int, Field(gt=0)]


class SubscriptionIdentity(ProviderModel):
    """Verified subscription result, matched against the actual request."""

    id: Identifier
    status: Literal["enabled"]
    type: Literal["channel.chat.message"]
    version: Literal["1"]
    condition: Condition
    transport: Transport


class SubscriptionResponse(ProviderModel):
    """Exactly one subscription must have been created."""

    data: Annotated[tuple[SubscriptionIdentity, ...], Field(min_length=1, max_length=1)]


def require_tls(context: ssl.SSLContext) -> None:
    """Custom CAs are permitted; hostname and certificate checks are mandatory."""
    if not context.check_hostname or context.verify_mode != ssl.CERT_REQUIRED:
        reject("origin")


class TwitchApi:
    """Bounded HTTPS client with explicit credentials and no redirects or retries."""

    def __init__(
        self, credentials: TwitchCredentials, tls: ssl.SSLContext | None = None
    ) -> None:
        """Retain explicit runtime credentials; do not perform network IO yet."""
        self.credentials: TwitchCredentials = credentials
        self.tls: ssl.SSLContext = tls or ssl.create_default_context()
        require_tls(self.tls)
        self._authorization: TwitchAuthorization | None = None
        self._valid_until: float = 0.0

    def _request(self, subscription: TwitchSubscription | None) -> bytes:
        """Use only the fixed validation/read-subscription endpoints."""
        require_tls(self.tls)
        token = self.credentials.token.get_secret_value()
        if not token or any(char.isspace() for char in token):
            reject("origin")
        url = "https://id.twitch.tv/oauth2/validate"
        method = "GET"
        headers = {"Authorization": f"OAuth {token}"}
        body: bytes | None = None
        expected_status = 200
        if subscription is not None:
            url = "https://api.twitch.tv/helix/eventsub/subscriptions"
            method = "POST"
            headers = {
                "Authorization": f"Bearer {token}",
                "Client-Id": self.credentials.client_id,
                "Content-Type": "application/json",
            }
            body = subscription.model_dump_json().encode()
            expected_status = 202
        headers["Accept-Encoding"] = "identity"
        with (
            httpx.Client(
                verify=self.tls,
                trust_env=False,
                follow_redirects=False,
                timeout=httpx.Timeout(10, connect=5),
                limits=httpx.Limits(max_connections=1),
            ) as client,
            client.stream(method, url, headers=headers, content=body) as response,
        ):
            if (
                response.status_code != expected_status
                or response.headers.get("Content-Encoding", "identity") != "identity"
            ):
                reject("origin")
            result = bytearray()
            for chunk in response.iter_raw(chunk_size=MAX_BYTES + 1):
                result.extend(chunk)
                if len(result) > MAX_BYTES:
                    reject("malformed")
            return bytes(result)

    def validate(self) -> TwitchAuthorization:
        """Validate the supplied token identity before any subscription creation."""
        if self._authorization is not None and time.monotonic() < self._valid_until:
            return self._authorization
        self._authorization = None
        identity = parse(TokenIdentity, self._request(None))
        if (
            identity.client_id != self.credentials.client_id
            or identity.user_id != self.credentials.reader_user_id
            or set(identity.scopes) != {"user:read:chat"}
        ):
            reject("origin")
        self._authorization = TwitchAuthorization(
            user_id=identity.user_id, scopes=("user:read:chat",)
        )
        self._valid_until = time.monotonic() + min(identity.expires_in, 3600)
        return self._authorization

    def subscribe(self, request: TwitchSubscription) -> Identifier:
        """Create only the enrolled user's bounded channel.chat.message subscription."""
        authorization = self.validate()
        if (
            request.condition.user_id != authorization.user_id
            or request.condition.broadcaster_user_id
            != self.credentials.broadcaster_user_id
        ):
            reject("origin")
        result = parse(SubscriptionResponse, self._request(request)).data[0]
        if (
            result.condition != request.condition
            or result.transport != request.transport
        ):
            reject("scope")
        return result.id
