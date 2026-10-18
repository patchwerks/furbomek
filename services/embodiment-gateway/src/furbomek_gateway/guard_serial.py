"""Persistent, serialized pySerial boundary for the guarded UART bridge."""

from dataclasses import dataclass, replace
from math import ceil
from typing import Final, final

import anyio
import serial

from furbomek_gateway.guard_models import GuardSettings
from furbomek_gateway.guard_protocol import (
    GuardCommand,
    GuardReply,
    GuardReplyOpcode,
    GuardResult,
    GuardState,
    encode_begin,
    encode_command,
    raw_stop,
)
from furbomek_gateway.guard_serial_errors import GuardSerialError, GuardSerialErrorCode
from furbomek_gateway.guard_serial_io import GuardSerialIO

_BAUDRATE: Final = 115200
_MAX_SEQUENCE: Final = 0x1FFFFF


def lease_lower_bound(board_remaining_ms: int, elapsed_seconds: float) -> int:
    """Subtract rounded elapsed time and the fixed freshness margin."""
    return max(0, board_remaining_ms - ceil(elapsed_seconds * 1000) - 10)


@dataclass(frozen=True, slots=True)
class StopExchange:
    """STOP write fact and optional firmware Fault verification."""

    frame_sent: bool
    reply: GuardReply | None


@dataclass(slots=True)
class BeginAttempt:
    """Attempt-local fact that the BEGIN write may have started."""

    write_started: bool = False


def _open_port(settings: GuardSettings) -> serial.Serial:
    return serial.Serial(
        port=settings.bridge_device_path,
        baudrate=_BAUDRATE,
        timeout=0,
        write_timeout=settings.exchange_timeout_seconds,
        exclusive=True,
    )


@final
class GuardSerialTransport:
    """One persistent POSIX UART whose exchanges never interleave bytes."""

    def __init__(self, settings: GuardSettings, port: serial.Serial) -> None:
        """Create a transport around an already-exclusive nonblocking port."""
        self._settings = settings
        self._port = port
        self._io = GuardSerialIO(port)
        self._lock = anyio.Lock()
        self._last_accepted_sequence = 0
        self._last_state: GuardState | None = None

    @classmethod
    async def open(cls, settings: GuardSettings) -> "GuardSerialTransport":
        """Open the one configured bridge path without exposing it to tools."""
        try:
            port = await anyio.to_thread.run_sync(_open_port, settings)
        except (serial.SerialException, ValueError) as error:
            raise GuardSerialError(GuardSerialErrorCode.CONNECTION) from error
        return cls(settings, port)

    async def aclose(self) -> None:
        """Close the long-lived port at the MCP server lifespan boundary."""
        async with self._lock:
            await anyio.to_thread.run_sync(self._port.close)

    async def begin(self, correlation: bytes) -> GuardReply:
        """Begin a fresh session with the exact zero-sequence BEGIN frame."""
        async with self._lock:
            reply = await self._exchange_locked(
                encode_begin(correlation), GuardReplyOpcode.BEGIN, None
            )
            if reply.result is GuardResult.ACCEPTED:
                self._last_accepted_sequence = reply.sequence
            return reply

    async def begin_state_aware(
        self, correlation: bytes, attempt: BeginAttempt | None = None
    ) -> GuardReply:
        """Synchronize BOOT or DISARMED state before allocating BEGIN sequence."""
        async with self._lock:
            status = await self._exchange_locked(
                encode_command(GuardCommand.STATUS, 0), GuardReplyOpcode.STATUS, None
            )
            if status.result is not GuardResult.ACCEPTED:
                raise GuardSerialError(GuardSerialErrorCode.PROTOCOL)
            match status.state:
                case GuardState.BOOT:
                    begin_sequence = 0
                case GuardState.DISARMED:
                    begin_sequence = status.sequence + 1
                    if begin_sequence > _MAX_SEQUENCE:
                        raise GuardSerialError(GuardSerialErrorCode.STALE_REPLY)
                case (
                    GuardState.SESSION
                    | GuardState.ARMING
                    | GuardState.ARMED
                    | GuardState.FAULT
                ):
                    raise GuardSerialError(GuardSerialErrorCode.PROTOCOL)
            if attempt is not None:
                attempt.write_started = True
            reply = await self._begin_after_sync(correlation, begin_sequence)
            if reply.result is GuardResult.ACCEPTED:
                self._last_accepted_sequence = begin_sequence
            return reply

    async def _begin_after_sync(
        self, correlation: bytes, begin_sequence: int
    ) -> GuardReply:
        return await self._exchange_locked(
            encode_begin(correlation, begin_sequence),
            GuardReplyOpcode.BEGIN,
            begin_sequence,
        )

    async def command(
        self, command: GuardCommand, *, action: int | None = None
    ) -> GuardReply:
        """Send one sequenced command and retain reply-derived sequence truth."""
        async with self._lock:
            sequence = self._next_sequence()
            reply = await self._exchange_locked(
                encode_command(command, sequence, action=action),
                GuardReplyOpcode(command + 1),
                sequence,
            )
            self._last_accepted_sequence = reply.sequence
            return reply

    async def supply(self) -> GuardReply:
        """Read supply without advancing local sequence or renewing a lease."""
        async with self._lock:
            return await self._exchange_locked(
                encode_command(GuardCommand.SUPPLY, 0), GuardReplyOpcode.SUPPLY, None
            )

    async def status_sync(self) -> GuardReply:
        """Read BOOT, DISARMED, or FAULT status without consuming a sequence."""
        async with self._lock:
            if self._last_state in (
                GuardState.SESSION,
                GuardState.ARMING,
                GuardState.ARMED,
            ):
                sequence = self._next_sequence()
                reply = await self._exchange_locked(
                    encode_command(GuardCommand.STATUS, sequence),
                    GuardReplyOpcode.STATUS,
                    sequence,
                )
            else:
                reply = await self._exchange_locked(
                    encode_command(GuardCommand.STATUS, 0),
                    GuardReplyOpcode.STATUS,
                    None,
                )
            if reply.result is GuardResult.ACCEPTED:
                self._last_accepted_sequence = reply.sequence
            return reply

    async def stop(self) -> StopExchange:
        """Send terminal raw STOP and validate its reply when it arrives."""
        async with self._lock:
            frame_sent = False
            try:
                with anyio.fail_after(self._settings.exchange_timeout_seconds):
                    await self._io.write(raw_stop())
                    frame_sent = True
                    reply = await self._io.read_matching(GuardReplyOpcode.STOP)
            except TimeoutError:
                return StopExchange(frame_sent=frame_sent, reply=None)
            except GuardSerialError:
                return StopExchange(frame_sent=frame_sent, reply=None)
        return StopExchange(frame_sent=frame_sent, reply=reply)

    def _next_sequence(self) -> int:
        sequence = self._last_accepted_sequence + 1
        if sequence > _MAX_SEQUENCE:
            raise GuardSerialError(GuardSerialErrorCode.STALE_REPLY)
        return sequence

    async def _exchange_locked(
        self, payload: bytes, expected: GuardReplyOpcode, sequence: int | None
    ) -> GuardReply:
        query = expected in (GuardReplyOpcode.KEEPALIVE, GuardReplyOpcode.STATUS)
        first_send: float | None = None
        retry_send: float | None = None
        reply: GuardReply | None = None
        for attempt in range(2 if query else 1):
            send_started = anyio.current_time()
            if attempt == 0:
                first_send = send_started
            else:
                retry_send = send_started
            try:
                with anyio.fail_after(self._settings.exchange_timeout_seconds):
                    await self._io.write(payload)
                    reply = await self._io.read_matching(
                        expected, sequence, allow_replay=attempt == 1
                    )
                break
            except TimeoutError as error:
                if not query or attempt == 1:
                    raise GuardSerialError(GuardSerialErrorCode.TIMEOUT) from error
        if reply is None:
            raise GuardSerialError(GuardSerialErrorCode.TIMEOUT)
        if reply.opcode is not expected:
            raise GuardSerialError(GuardSerialErrorCode.STALE_REPLY)
        self._last_state = reply.state
        if query:
            send_reference = (
                retry_send
                if reply.result is GuardResult.QUERY_REPLAY and retry_send is not None
                else first_send
            )
            if send_reference is None:
                raise GuardSerialError(GuardSerialErrorCode.STALE_REPLY)
            lease_lower_bound_ms = lease_lower_bound(
                reply.remaining_ms or 0,
                anyio.current_time() - send_reference,
            )
            reply = replace(reply, lease_lower_bound_ms=lease_lower_bound_ms)
        if (
            sequence is not None
            and reply.result in (GuardResult.ACCEPTED, GuardResult.QUERY_REPLAY)
            and reply.sequence != sequence
            and not (
                expected is GuardReplyOpcode.STATUS
                and reply.state
                in (
                    GuardState.BOOT,
                    GuardState.DISARMED,
                    GuardState.FAULT,
                )
            )
        ):
            raise GuardSerialError(GuardSerialErrorCode.STALE_REPLY)
        return reply
