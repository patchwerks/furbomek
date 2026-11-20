"""Owner-only Mac edge listeners and lifetime management."""

import fcntl
import os
import signal
import stat
from collections.abc import Awaitable, Callable
from contextlib import suppress
from pathlib import Path
from typing import ClassVar, assert_never, final

import anyio
from anyio.abc import SocketStream
from anyio.streams.buffered import BufferedByteReceiveStream
from pydantic import BaseModel, ConfigDict, ValidationError

from furbomek_gateway.edge_media import MacMedia, MediaSettings
from furbomek_gateway.edge_protocol import (
    MESSAGE_LIMIT,
    REMOTE_REQUEST,
    EdgeReply,
    KinectRequest,
    ObsRequest,
    OperatorRequest,
    RobotRequest,
)
from furbomek_gateway.edge_robot import RobotBench
from furbomek_gateway.edge_ssh import LinkSettings, ReverseLink
from furbomek_gateway.guard_models import GuardSettings


class EdgeSettings(BaseModel):
    """Private host configuration read only at startup."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)
    media: MediaSettings
    guard: GuardSettings
    link: LinkSettings
    require_kinect_lock_for_motion: bool = False


async def _disconnect(stream: SocketStream, scope: anyio.CancelScope) -> None:
    with suppress(
        anyio.EndOfStream,
        anyio.BrokenResourceError,
        anyio.ClosedResourceError,
        OSError,
    ):
        _ = await stream.receive(1)
    scope.cancel()


async def serve_request(
    stream: SocketStream,
    dispatch: Callable[[bytes], Awaitable[EdgeReply]],
) -> None:
    """Serve one request and cancel it if its client leaves."""
    async with stream:
        try:
            with anyio.fail_after(1):
                buf = BufferedByteReceiveStream(stream)
                raw = await buf.receive_until(b"\n", MESSAGE_LIMIT)
                if buf.buffer:
                    return
            async with anyio.create_task_group() as session:
                _ = session.start_soon(_disconnect, stream, session.cancel_scope)
                try:
                    with anyio.fail_after(10):
                        reply = await dispatch(raw)
                        await stream.send(
                            reply.model_dump_json(exclude_none=True).encode() + b"\n"
                        )
                except (
                    OSError,
                    TimeoutError,
                    anyio.BrokenResourceError,
                    anyio.ClosedResourceError,
                ):
                    return
                finally:
                    session.cancel_scope.cancel()
        except (
            OSError,
            TimeoutError,
            anyio.EndOfStream,
            anyio.IncompleteRead,
            anyio.DelimiterNotFound,
            anyio.BrokenResourceError,
            anyio.ClosedResourceError,
        ):
            return


@final
class EdgeHost:
    """Route separate remote and local commands to the owned devices."""

    def __init__(self, settings: EdgeSettings) -> None:
        """Construct closed device owners from private settings."""
        self.media = MacMedia(settings.media)
        observation = (
            self._robot_tracked if settings.require_kinect_lock_for_motion else None
        )
        self.bench = RobotBench(settings.guard, observation)

    def _robot_tracked(self) -> bool:
        health = self.media.health()
        return health.fresh and health.object_locked

    async def remote(self, data: bytes) -> EdgeReply:
        """Decode and dispatch only remote semantic commands."""
        try:
            request = REMOTE_REQUEST.validate_json(data, strict=True)
        except ValidationError:
            return EdgeReply(result="invalid", state="unrecognized_remote_request")
        safe_stop = isinstance(request, RobotRequest) and request.command == "stop"
        if not request.fresh() and not safe_stop:
            return EdgeReply(result="refused", state="stale_request")
        match request:
            case RobotRequest():
                return await self.bench.remote(request)
            case KinectRequest():
                return await self.media.camera(request.command)
            case ObsRequest():
                return await self.media.obs(request.command)
        assert_never(request)

    async def operator(self, data: bytes) -> EdgeReply:
        """Decode a local bench authorization command."""
        try:
            request = OperatorRequest.model_validate_json(data, strict=True)
        except ValidationError:
            return EdgeReply(result="invalid", state="unrecognized_operator_request")
        if not request.fresh():
            return EdgeReply(result="refused", state="stale_request")
        return await self.bench.operator(request.command)

    async def run_remote(self, stream: SocketStream) -> None:
        """Handle a connection to the forwarded socket."""
        await serve_request(stream, self.remote)

    async def run_operator(self, stream: SocketStream) -> None:
        """Handle a connection to the local operator socket."""
        await serve_request(stream, self.operator)

    async def watch(self) -> None:
        """Expire bench access and clear failed media workers."""
        while True:
            self.bench.expire()
            await self.media.check_workers()
            await anyio.sleep(0.25)


def _private_root(directory: Path) -> None:
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = directory.lstat()
    if (
        not stat.S_ISDIR(info.st_mode)
        or info.st_uid != os.getuid()
        or info.st_mode & 0o077
    ):
        message = "Mac edge directory is not owner-only"
        raise PermissionError(message)


async def run_edge(settings: EdgeSettings) -> None:
    """Run one edge owner and stop its workers on shutdown."""
    _ = os.umask(0o077)
    runtime = settings.media.runtime
    _private_root(runtime)
    with (runtime / "edge.lock").open("ab") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        control = runtime / "control.sock"
        operator = runtime / "operator.sock"
        control.unlink(missing_ok=True)
        operator.unlink(missing_ok=True)
        edge = EdgeHost(settings)
        activity_path = edge.media.frames / "activity.json"
        activity_path.unlink(missing_ok=True)
        link = ReverseLink(settings.link, control, activity_path)
        try:
            async with (
                await anyio.create_unix_listener(control, mode=0o600) as remote,
                await anyio.create_unix_listener(operator, mode=0o600) as local,
                anyio.create_task_group() as tasks,
            ):
                _ = tasks.start_soon(remote.serve, edge.run_remote)
                _ = tasks.start_soon(local.serve, edge.run_operator)
                _ = tasks.start_soon(link.run, edge.bench)
                _ = tasks.start_soon(edge.watch)
                with anyio.open_signal_receiver(
                    signal.SIGTERM, signal.SIGINT
                ) as signals:
                    _ = await anext(signals)
                tasks.cancel_scope.cancel()
        finally:
            with anyio.CancelScope(shield=True):
                _ = await edge.bench.operator("close")
                await edge.media.close()
                control.unlink(missing_ok=True)
                operator.unlink(missing_ok=True)
