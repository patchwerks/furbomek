"""AnyIO transport for the bounded stock Freenove delimiter protocol."""

from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar, Final, override

import anyio
from anyio.abc import ByteStream

from furbomek_gateway.models import ErrorCode, GatewaySettings

_FRAME_START: Final = 0x80
_FRAME_END: Final = 0x81
_MAX_FRAME_BYTES: Final = 32
_ECHO_REQUEST: Final = bytes((_FRAME_START, 0, _FRAME_END))
_ECHO_RESPONSE: Final = bytes((_FRAME_START, 1, _FRAME_END))
_SUPPLY_REQUEST: Final = bytes((_FRAME_START, 10, _FRAME_END))
_SUPPLY_RESPONSE_LENGTH: Final = 5
_SUPPLY_RESPONSE_OPCODE: Final = 11
_MAX_DATA_BYTE: Final = 127
_SUPPLY_BASE: Final = 128
_SUPPLY_SCALE: Final = 100


class StockTransportError(Exception):
    """Base class for non-sensitive stock transport failures."""

    error_code: ClassVar[ErrorCode]


class StockConnectionError(StockTransportError):
    """The configured stock endpoint could not be reached."""

    error_code: ClassVar[ErrorCode] = ErrorCode.CONNECTION_FAILED

    @override
    def __str__(self) -> str:
        """Return a non-sensitive failure code."""
        return "stock transport connection failed"


class StockTimeoutError(StockTransportError):
    """The stock request exceeded its bounded timeout."""

    error_code: ClassVar[ErrorCode] = ErrorCode.TIMEOUT

    @override
    def __str__(self) -> str:
        """Return a non-sensitive failure code."""
        return "stock transport timed out"


class ProtocolErrorCode(StrEnum):
    """Bounded parser rejection categories."""

    BAD_START = "bad_start"
    BAD_END = "bad_end"
    BAD_OPCODE = "bad_opcode"
    TRUNCATED = "truncated"
    FRAME_TOO_LARGE = "frame_too_large"


class StockProtocolError(StockTransportError):
    """The stock response did not match the bounded protocol grammar."""

    error_code: ClassVar[ErrorCode] = ErrorCode.INVALID_RESPONSE
    code: ProtocolErrorCode

    def __init__(self, code: ProtocolErrorCode) -> None:
        """Create a typed protocol rejection."""
        super().__init__()
        self.code = code

    @override
    def __str__(self) -> str:
        """Return a non-sensitive protocol rejection code."""
        return f"stock protocol rejected response: {self.code.value}"


@dataclass(frozen=True, slots=True)
class SupplyReading:
    """Decoded controller-reported supply value."""

    volts: float


async def _read_frame(stream: ByteStream) -> bytes:
    frame = bytearray()
    for index in range(_MAX_FRAME_BYTES):
        try:
            chunk = await stream.receive(1)
        except anyio.EndOfStream as error:
            raise StockProtocolError(ProtocolErrorCode.TRUNCATED) from error
        if not chunk:
            raise StockProtocolError(ProtocolErrorCode.TRUNCATED)
        byte = chunk[0]
        if index == 0 and byte != _FRAME_START:
            raise StockProtocolError(ProtocolErrorCode.BAD_START)
        if index > 0 and byte >= _FRAME_START:
            if byte == _FRAME_END:
                return bytes((*frame, byte))
            raise StockProtocolError(ProtocolErrorCode.BAD_END)
        frame.append(byte)
    raise StockProtocolError(ProtocolErrorCode.FRAME_TOO_LARGE)


class StockTcpTransport:
    """Serialized, read-only access to the stock delimiter TCP protocol."""

    def __init__(self, settings: GatewaySettings) -> None:
        """Create a transport with one serialized request lock."""
        self._settings: GatewaySettings = settings
        self._lock: anyio.Lock = anyio.Lock()

    async def get_state(self) -> None:
        """Validate the exact stock echo response."""
        async with self._lock:
            response = await self._request(_ECHO_REQUEST)
        if response != _ECHO_RESPONSE:
            raise StockProtocolError(ProtocolErrorCode.BAD_OPCODE)

    async def get_supply_voltage(self) -> SupplyReading:
        """Read the stock controller-reported supply encoding."""
        async with self._lock:
            response = await self._request(_SUPPLY_REQUEST)
        if (
            len(response) != _SUPPLY_RESPONSE_LENGTH
            or response[1] != _SUPPLY_RESPONSE_OPCODE
        ):
            raise StockProtocolError(ProtocolErrorCode.BAD_OPCODE)
        high, low = response[2], response[3]
        if high > _MAX_DATA_BYTE or low > _MAX_DATA_BYTE:
            raise StockProtocolError(ProtocolErrorCode.BAD_OPCODE)
        return SupplyReading(volts=(_SUPPLY_BASE * high + low) / _SUPPLY_SCALE)

    async def _request(self, request: bytes) -> bytes:
        try:
            with anyio.fail_after(self._settings.timeout_seconds):
                async with await anyio.connect_tcp(
                    str(self._settings.host), self._settings.port
                ) as stream:
                    await stream.send(request)
                    return await _read_frame(stream)
        except TimeoutError as error:
            raise StockTimeoutError from error
        except (OSError, anyio.BrokenResourceError, anyio.ClosedResourceError) as error:
            raise StockConnectionError from error
