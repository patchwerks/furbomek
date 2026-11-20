from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

import anyio
import pytest

from furbomek_gateway.edge_host import EdgeHost, EdgeSettings, serve_request
from furbomek_gateway.edge_media import MediaSettings
from furbomek_gateway.edge_protocol import (
    EdgeReply,
    KinectRequest,
    OperatorRequest,
    exchange,
    unix_ms,
)
from furbomek_gateway.edge_ssh import LinkSettings
from tests.guard_settings import powered_settings


@asynccontextmanager
async def _remote_socket(tmp_path: Path) -> AsyncGenerator[Path]:
    unused = tmp_path / "unconfigured"
    edge = EdgeHost(
        EdgeSettings(
            media=MediaSettings(
                runtime=tmp_path,
                repository=unused,
                media_root=unused,
                capture=unused,
                tracker_python=unused,
                godot=unused,
            ),
            guard=powered_settings(str(unused)),
            link=LinkSettings(host="brodex", relay_command=("unconfigured",)),
        )
    )
    with TemporaryDirectory(prefix="fmk-edge-") as directory:
        socket = Path(directory) / "control"
        async with (
            await anyio.create_unix_listener(socket, mode=0o600) as listener,
            anyio.create_task_group() as tasks,
        ):
            _ = tasks.start_soon(listener.serve, edge.run_remote)
            try:
                yield socket
            finally:
                tasks.cancel_scope.cancel()


@pytest.mark.anyio
async def test_forwarded_socket_rejects_local_operator_command(tmp_path: Path) -> None:
    async with _remote_socket(tmp_path) as socket:
        result = await exchange(
            socket, OperatorRequest(command="enable", issued_ms=unix_ms())
        )
    assert result.result == "invalid"


@pytest.mark.anyio
async def test_delayed_start_is_rejected_before_camera_start(tmp_path: Path) -> None:
    async with _remote_socket(tmp_path) as socket:
        result = await exchange(socket, KinectRequest(command="start", issued_ms=0))
    assert result.result == "refused"


@pytest.mark.anyio
async def test_request_is_cancelled_when_its_client_disconnects() -> None:
    started = anyio.Event()
    cancelled = anyio.Event()

    async def dispatch(_: bytes) -> EdgeReply:
        started.set()
        try:
            await anyio.sleep_forever()
        finally:
            cancelled.set()
        pytest.fail("The blocked dispatch must exit by cancellation")

    with TemporaryDirectory(prefix="fmk-edge-") as directory:
        socket = Path(directory) / "control"
        async with (
            await anyio.create_unix_listener(socket, mode=0o600) as listener,
            anyio.create_task_group() as tasks,
        ):

            async def serve() -> None:
                async with await listener.accept() as peer:
                    await serve_request(peer, dispatch)

            _ = tasks.start_soon(serve)
            with anyio.fail_after(2):
                async with await anyio.connect_unix(socket) as client:
                    await client.send(b"{}\n")
                    await started.wait()
                await cancelled.wait()
