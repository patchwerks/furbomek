from ipaddress import IPv4Address

import anyio
import pytest

from furbomek_gateway.models import GatewaySettings
from furbomek_gateway.transport import (
    ProtocolErrorCode,
    StockConnectionError,
    StockProtocolError,
    StockTcpTransport,
    StockTimeoutError,
)
from tests.support import wire_server


def make_settings(port: int, timeout_seconds: float = 0.5) -> GatewaySettings:
    return GatewaySettings(
        host=IPv4Address("127.0.0.1"),
        port=port,
        timeout_seconds=timeout_seconds,
    )


@pytest.mark.anyio
async def test_echo_accepts_fragmented_stock_response() -> None:
    async with wire_server(lambda _: b"\x80\x01\x81", fragmented=True) as fixture:
        transport = StockTcpTransport(make_settings(fixture.port))

        await transport.get_state()

        assert fixture.received == [b"\x80\x00\x81"]


@pytest.mark.anyio
async def test_supply_decodes_controller_reported_value() -> None:
    async with wire_server(lambda _: b"\x80\x0b\x01\x02\x81") as fixture:
        transport = StockTcpTransport(make_settings(fixture.port))

        reading = await transport.get_supply_voltage()

        assert reading.volts == 1.3
        assert fixture.received == [b"\x80\x0a\x81"]


@pytest.mark.anyio
@pytest.mark.parametrize(
    "response",
    [b"\x80\x0b\x80\x00\x81", b"\x80\x0b\x00\x80\x81"],
)
async def test_supply_rejects_out_of_range_byte(response: bytes) -> None:
    async with wire_server(lambda _: response) as fixture:
        transport = StockTcpTransport(make_settings(fixture.port))

        with pytest.raises(StockProtocolError) as raised:
            _ = await transport.get_supply_voltage()

        assert raised.value.code is ProtocolErrorCode.BAD_END


@pytest.mark.anyio
async def test_requests_are_serialized_per_transport_instance() -> None:
    async with wire_server(
        lambda _: b"\x80\x01\x81",
        delay_seconds=0.02,
    ) as fixture:
        transport = StockTcpTransport(make_settings(fixture.port))
        async with anyio.create_task_group() as task_group:
            _ = task_group.start_soon(transport.get_state)
            _ = task_group.start_soon(transport.get_state)

        assert fixture.max_active == [1]


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("response", "code"),
    [
        (b"\x80\x02\x81", ProtocolErrorCode.BAD_OPCODE),
        (b"\x80\x01\x82", ProtocolErrorCode.BAD_END),
        (b"\x80\x01", ProtocolErrorCode.TRUNCATED),
    ],
)
async def test_rejects_invalid_stock_response(
    response: bytes,
    code: ProtocolErrorCode,
) -> None:
    async with wire_server(lambda _: response) as fixture:
        transport = StockTcpTransport(make_settings(fixture.port))

        with pytest.raises(StockProtocolError) as raised:
            await transport.get_state()

        assert raised.value.code is code


@pytest.mark.anyio
async def test_timeout_is_typed_and_bounded() -> None:
    async with wire_server(
        lambda _: b"\x80\x01\x81",
        delay_seconds=0.05,
    ) as fixture:
        transport = StockTcpTransport(make_settings(fixture.port, 0.01))

        with pytest.raises(StockTimeoutError):
            await transport.get_state()


@pytest.mark.anyio
async def test_refused_connection_is_typed() -> None:
    listener = await anyio.create_tcp_listener(
        local_host="127.0.0.1",
        local_port=0,
    )
    port = int(listener.listeners[0].extra(anyio.abc.SocketAttribute.local_port))
    await listener.aclose()
    transport = StockTcpTransport(make_settings(port, 0.2))

    with pytest.raises(StockConnectionError):
        await transport.get_state()
