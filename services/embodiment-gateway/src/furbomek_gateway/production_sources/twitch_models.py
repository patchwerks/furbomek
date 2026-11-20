"""Version-one EventSub chat projections; irrelevant provider fields are dropped."""

from typing import Annotated, ClassVar, Literal

from pydantic import ConfigDict, Field, JsonValue

from furbomek_gateway.effect_contracts import Contract, Identifier


class ProviderModel(Contract):
    """Strict consumed fields with forward-compatible unconsumed provider fields."""

    model_config: ClassVar[ConfigDict] = ConfigDict(
        extra="ignore",
        strict=True,
        frozen=True,
    )


class Metadata(ProviderModel):
    """EventSub envelope discriminator and provider timestamp."""

    message_id: Identifier
    message_type: Literal[
        "notification",
        "session_welcome",
        "session_keepalive",
        "session_reconnect",
        "revocation",
    ]
    message_timestamp: Annotated[str, Field(max_length=40)]
    subscription_type: Literal["channel.chat.message"] | None = None
    subscription_version: Literal["1"] | None = None


class Frame(ProviderModel):
    """Transport controls are observed without interpreting their URLs."""

    metadata: Metadata
    payload: JsonValue


class Condition(ProviderModel):
    """Expected broadcaster and OAuth reader identity."""

    broadcaster_user_id: Identifier
    user_id: Identifier


class Transport(ProviderModel):
    """EventSub websocket session binding."""

    method: Literal["websocket"]
    session_id: Identifier


class Subscription(ProviderModel):
    """Only the enrolled enabled chat subscription can produce requests."""

    id: Identifier
    status: Literal["enabled"]
    type: Literal["channel.chat.message"]
    version: Literal["1"]
    condition: Condition
    transport: Transport


class Message(ProviderModel):
    """Raw text is consumed only by an exact local allowlist."""

    text: Annotated[str, Field(min_length=1, max_length=500)]


class ChatEvent(ProviderModel):
    """Only event identity and bounded text enter the adapter."""

    broadcaster_user_id: Identifier
    chatter_user_id: Identifier
    message_id: Identifier
    message: Message
    source_broadcaster_user_id: Identifier | None = None


class Notification(ProviderModel):
    """Typed notification payload, never a caller-supplied private event."""

    subscription: Subscription
    event: ChatEvent
