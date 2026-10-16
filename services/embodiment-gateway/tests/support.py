from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass

import anyio
from anyio.abc import SocketAttribute, SocketStream


@dataclass(frozen=True, slots=True)
class WireCapture:
    received: list[bytes]
    port: int
    max_active: list[int]


@asynccontextmanager
async def wire_server(
    response_for: Callable[[bytes], bytes],
    *,
    fragmented: bool = False,
    delay_seconds: float = 0.0,
) -> AsyncGenerator[WireCapture, None]:
    listener = await anyio.create_tcp_listener(
        local_host="127.0.0.1",
        local_port=0,
    )
    capture = WireCapture(
        received=[],
        port=int(listener.listeners[0].extra(SocketAttribute.local_port)),
        max_active=[0],
    )
    active = [0]

    async def handle(stream: SocketStream) -> None:
        async with stream:
            active[0] += 1
            capture.max_active[0] = max(capture.max_active[0], active[0])
            try:
                request = await stream.receive(32)
                capture.received.append(request)
                if delay_seconds > 0:
                    await anyio.sleep(delay_seconds)
                response = response_for(request)
                chunks = (
                    tuple(bytes((byte,)) for byte in response)
                    if fragmented
                    else (response,)
                )
                for chunk in chunks:
                    await stream.send(chunk)
            finally:
                active[0] -= 1

    async with listener, anyio.create_task_group() as task_group:
        _ = task_group.start_soon(listener.serve, handle)
        try:
            yield capture
        finally:
            task_group.cancel_scope.cancel()
