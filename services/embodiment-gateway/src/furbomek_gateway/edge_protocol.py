"""Bounded messages carried by the private Mac edge sockets."""

from pathlib import Path
from typing import Annotated, ClassVar, Final, Literal

import anyio
from anyio.streams.buffered import BufferedByteReceiveStream
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from furbomek_gateway import edge_time
from furbomek_gateway.guard_models import (
    ActionName,
    GuardCapabilitiesResult,
    GuardStateResult,
    GuardStopResult,
    GuardSupplyVoltageResult,
    PoweredActionResult,
)
from furbomek_gateway.production_control import ProductionReply, ProductionRequest

type KinectCommand = Literal["status", "start", "stop", "rgb", "crimson", "xyz"]
type ObsCommand = Literal[
    "open",
    "status",
    "start_recording",
    "stop_recording",
    "start_test_stream",
    "stop_streaming",
]
type RobotQuery = Literal["state", "voltage", "capabilities", "stop"]
type OperatorCommand = Literal["prepare", "enable", "close"]
type ResultCode = Literal["ok", "starting", "refused", "unavailable", "invalid"]
type RobotResult = (
    GuardStateResult
    | GuardSupplyVoltageResult
    | GuardCapabilitiesResult
    | PoweredActionResult
    | GuardStopResult
)
MESSAGE_LIMIT: Final = 8192
CLOCK_SKEW_MS: Final = edge_time.CLOCK_SKEW_MS
REQUEST_AGE_MS: Final = edge_time.REQUEST_AGE_MS


def unix_ms() -> int:
    """Preserve the public edge time helper for existing callers."""
    return edge_time.unix_ms()


class _Message(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)


class _Request(_Message):
    issued_ms: int = Field(ge=0)

    def fresh(self) -> bool:
        """Allow limited clock skew with a short maximum wire age."""
        return -CLOCK_SKEW_MS <= unix_ms() - self.issued_ms <= REQUEST_AGE_MS


class RobotRequest(_Request):
    """Named guarded robot request."""

    target: Literal["robot"] = "robot"
    command: ActionName | RobotQuery


class KinectRequest(_Request):
    """Named private capture and display request."""

    target: Literal["kinect"] = "kinect"
    command: KinectCommand


class ObsRequest(_Request):
    """Named action against the dedicated OBS session."""

    target: Literal["obs"] = "obs"
    command: ObsCommand


class OperatorRequest(_Request):
    """Local-only bench authorization request."""

    target: Literal["operator"] = "operator"
    command: OperatorCommand


type RemoteRequest = RobotRequest | KinectRequest | ObsRequest | ProductionRequest
REMOTE_REQUEST: Final[TypeAdapter[RemoteRequest]] = TypeAdapter(
    Annotated[RemoteRequest, Field(discriminator="target")]
)


class KinectHealth(_Message):
    """Observed capture and tracking state, with no raw media."""

    running: bool
    fresh: bool
    sequence: int | None = None
    capture_fps: float | None = None
    object_locked: bool = False


class ObsHealth(_Message):
    """OBS frontend state reported by the local script."""

    request_id: str
    result: ResultCode
    recording: bool
    streaming: bool
    source_bound: bool
    test_mode: bool


class EdgeReply(_Message):
    """One result from the Mac, with only public status fields."""

    result: ResultCode
    state: str
    robot: RobotResult | None = None
    kinect: KinectHealth | None = None
    obs: ObsHealth | None = None
    production: ProductionReply | None = None


async def exchange(path: Path, request: RemoteRequest | OperatorRequest) -> EdgeReply:
    """Send exactly one request. Never retry an uncertain outcome."""
    try:
        with anyio.fail_after(12):
            async with await anyio.connect_unix(path) as stream:
                await stream.send(request.model_dump_json().encode() + b"\n")
                buffer = BufferedByteReceiveStream(stream)
                reply = await buffer.receive_until(b"\n", MESSAGE_LIMIT)
                return EdgeReply.model_validate_json(reply)
    except (
        OSError,
        TimeoutError,
        anyio.EndOfStream,
        anyio.IncompleteRead,
        anyio.DelimiterNotFound,
        anyio.BrokenResourceError,
        ValidationError,
    ):
        return EdgeReply(result="unavailable", state="mac_edge_unreachable_or_no_reply")
