"""Strict codec for the guarded USB-to-RF UART protocol."""

from dataclasses import dataclass
from enum import IntEnum, StrEnum
from typing import Final, final, override

_START: Final = 0x80
_END: Final = 0x81
_FRAME_OVERHEAD: Final = 6
_STANDARD_BODY_LENGTH: Final = 10
_MAX_BODY_LENGTH: Final = 32
_MAX_SEQUENCE: Final = 0x1FFFFF
_MAX_DATA_BYTE: Final = 0x7F
_MAX_CRC_HIGH: Final = 3
_CORRELATION_BYTES: Final = 8
_MAX_ACTION: Final = 7


class GuardCommand(IntEnum):
    """Guard request opcodes permitted by the isolated adapter."""

    BEGIN = 0x28
    ARM = 0x2A
    KEEPALIVE = 0x2C
    EXEC = 0x2E
    STOP = 0x30
    STATUS = 0x32
    SUPPLY = 0x34
    DISARM = 0x36


class GuardReplyOpcode(IntEnum):
    """Odd reply opcodes accepted from the guarded bridge."""

    BEGIN = 0x29
    ARM = 0x2B
    KEEPALIVE = 0x2D
    EXEC = 0x2F
    STOP = 0x31
    STATUS = 0x33
    SUPPLY = 0x35
    DISARM = 0x37


class GuardResult(IntEnum):
    """Guard protocol result values."""

    ACCEPTED = 0
    MALFORMED = 1
    BAD_CRC = 2
    WRONG_STATE = 3
    BAD_SEQUENCE = 4
    UNSUPPORTED = 5
    BAD_METADATA = 6
    BUSY = 7
    EXPIRED = 8
    TIMEOUT = 9
    QUERY_REPLAY = 10


class GuardState(IntEnum):
    """Guard protocol states."""

    BOOT = 0
    SESSION = 1
    ARMING = 2
    ARMED = 3
    FAULT = 4
    DISARMED = 5


class GuardAction(IntEnum):
    """Closed semantic actions accepted by the powered Guard path."""

    ACTIVE = 0
    SLEEP = 1
    FORWARD = 2
    BACKWARD = 3
    LEFT = 4
    RIGHT = 5
    TURN_LEFT = 6
    TURN_RIGHT = 7


class GuardProtocolErrorCode(StrEnum):
    """Closed parser rejection categories."""

    CORRELATION = "correlation"
    SEQUENCE = "sequence"
    ACTION = "action"
    TRUNCATED = "truncated"
    FRAME = "frame"
    CRC = "crc"
    OPCODE = "opcode"
    RESULT = "result"
    STATE = "state"


@final
class GuardProtocolError(Exception):
    """A received or generated guard frame violated the closed grammar."""

    def __init__(self, code: GuardProtocolErrorCode) -> None:
        """Create an error that does not disclose serial data."""
        super().__init__()
        self.code = code

    @override
    def __str__(self) -> str:
        """Return the stable protocol error category."""
        return f"guard protocol rejected frame: {self.code.value}"


@dataclass(frozen=True, slots=True)
class GuardReply:
    """Validated reply data with supply-specific field interpretation."""

    opcode: GuardReplyOpcode
    result: GuardResult
    state: GuardState
    sequence: int
    remaining_ms: int | None
    supply_voltage_volts: float | None
    fault: int
    busy: bool
    lease_lower_bound_ms: int | None = None


def _crc16_ccitt_false(data: bytes) -> int:
    value = 0xFFFF
    for byte in data:
        value ^= byte << 8
        for _ in range(8):
            value = (
                ((value << 1) ^ 0x1021) & 0xFFFF
                if value & 0x8000
                else (value << 1) & 0xFFFF
            )
    return value


def _sequence_bytes(sequence: int) -> bytes:
    if not 0 <= sequence <= _MAX_SEQUENCE:
        raise GuardProtocolError(GuardProtocolErrorCode.SEQUENCE)
    return bytes(
        (
            sequence & _MAX_DATA_BYTE,
            (sequence >> 7) & _MAX_DATA_BYTE,
            (sequence >> 14) & _MAX_DATA_BYTE,
        )
    )


def _frame(body: bytes) -> bytes:
    checksum = _crc16_ccitt_false(bytes((len(body),)) + body)
    return bytes(
        (
            _START,
            len(body),
            *body,
            checksum & _MAX_DATA_BYTE,
            (checksum >> 7) & _MAX_DATA_BYTE,
            checksum >> 14,
            _END,
        )
    )


def encode_begin(correlation: bytes, sequence: int = 0) -> bytes:
    """Encode BEGIN with exactly eight CSPRNG bytes for correlation only."""
    if len(correlation) != _CORRELATION_BYTES:
        raise GuardProtocolError(GuardProtocolErrorCode.CORRELATION)
    identifier = bytes(
        component
        for byte in correlation
        for component in (byte & _MAX_DATA_BYTE, byte >> 7)
    )
    return _frame(bytes((GuardCommand.BEGIN, *_sequence_bytes(sequence))) + identifier)


def encode_command(
    command: GuardCommand, sequence: int, *, action: int | None = None
) -> bytes:
    """Encode one non-BEGIN command from the restricted adapter command set."""
    sequence_bytes = _sequence_bytes(sequence)
    match command:
        case (
            GuardCommand.ARM
            | GuardCommand.KEEPALIVE
            | GuardCommand.STATUS
            | GuardCommand.SUPPLY
            | GuardCommand.DISARM
        ):
            if action is not None:
                raise GuardProtocolError(GuardProtocolErrorCode.ACTION)
            return _frame(bytes((command,)) + sequence_bytes)
        case GuardCommand.EXEC:
            if action is None or not 0 <= action <= _MAX_ACTION:
                raise GuardProtocolError(GuardProtocolErrorCode.ACTION)
            return _frame(bytes((command,)) + sequence_bytes + bytes((action,)))
        case GuardCommand.BEGIN | GuardCommand.STOP:
            raise GuardProtocolError(GuardProtocolErrorCode.ACTION)


def raw_stop() -> bytes:
    """Return the firmware-defined unconditional terminal STOP sequence."""
    return bytes((_START, GuardCommand.STOP, _END))


def decode_reply(frame: bytes) -> GuardReply:  # noqa: C901
    """Decode one complete CRC-validated Guard reply frame."""
    if len(frame) < _FRAME_OVERHEAD or frame[0] != _START or frame[-1] != _END:
        raise GuardProtocolError(GuardProtocolErrorCode.TRUNCATED)
    body_length = frame[1]
    if len(frame) != body_length + _FRAME_OVERHEAD:
        raise GuardProtocolError(GuardProtocolErrorCode.FRAME)
    if body_length != _STANDARD_BODY_LENGTH:
        raise GuardProtocolError(GuardProtocolErrorCode.FRAME)
    if any(byte > _MAX_DATA_BYTE for byte in frame[1:-1]) or frame[-2] > _MAX_CRC_HIGH:
        raise GuardProtocolError(GuardProtocolErrorCode.FRAME)
    crc_start = 2 + body_length
    expected_crc = _crc16_ccitt_false(frame[1:crc_start])
    received_crc = (
        frame[crc_start] | (frame[crc_start + 1] << 7) | (frame[crc_start + 2] << 14)
    )
    if expected_crc != received_crc:
        raise GuardProtocolError(GuardProtocolErrorCode.CRC)
    body = frame[2 : 2 + body_length]
    try:
        opcode = GuardReplyOpcode(body[0])
    except ValueError as error:
        raise GuardProtocolError(GuardProtocolErrorCode.OPCODE) from error
    try:
        result = GuardResult(body[1])
    except ValueError as error:
        raise GuardProtocolError(GuardProtocolErrorCode.RESULT) from error
    if result is GuardResult.QUERY_REPLAY and opcode not in (
        GuardReplyOpcode.KEEPALIVE,
        GuardReplyOpcode.STATUS,
    ):
        raise GuardProtocolError(GuardProtocolErrorCode.RESULT)
    try:
        state = GuardState(body[2])
    except ValueError as error:
        raise GuardProtocolError(GuardProtocolErrorCode.STATE) from error
    sequence = body[3] | (body[4] << 7) | (body[5] << 14)
    value = body[6] | (body[7] << 7)
    if body[9] not in (0, 1):
        raise GuardProtocolError(GuardProtocolErrorCode.FRAME)
    supply = value / 100 if opcode is GuardReplyOpcode.SUPPLY else None
    remaining = None if supply is not None else value
    return GuardReply(
        opcode, result, state, sequence, remaining, supply, body[8], bool(body[9])
    )
