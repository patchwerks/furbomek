"""Framed receive and write mechanics for the guarded serial transport."""

from dataclasses import dataclass, field

import anyio
import serial

from furbomek_gateway.guard_protocol import (
    GuardProtocolError,
    GuardReply,
    GuardReplyOpcode,
    GuardResult,
    GuardState,
    decode_reply,
)
from furbomek_gateway.guard_serial_errors import GuardSerialError, GuardSerialErrorCode

_FRAME_START = 0x80
_FRAME_OVERHEAD = 6
_FRAME_HEADER_LENGTH = 2
_MAX_FRAME_LENGTH = 38
_POLL_SECONDS = 0.002
_STOP_FAULT_CODE = 4


@dataclass(slots=True)
class GuardSerialIO:
    """Own the durable receive buffer and nonblocking serial operations."""

    port: serial.Serial
    receive_buffer: bytearray = field(default_factory=bytearray)

    async def write(self, payload: bytes) -> None:
        """Write one complete frame."""
        try:
            count = await anyio.to_thread.run_sync(self.port.write, payload)
        except (serial.SerialException, serial.SerialTimeoutException) as error:
            raise GuardSerialError(GuardSerialErrorCode.WRITE) from error
        if count != len(payload):
            raise GuardSerialError(GuardSerialErrorCode.WRITE)

    async def read_matching(  # noqa: C901
        self,
        expected: GuardReplyOpcode,
        sequence: int | None = None,
        *,
        allow_replay: bool = False,
    ) -> GuardReply:
        """Drain stale replies until the expected fresh reply arrives."""
        while True:
            reply = await self._read_reply()
            if (
                reply.result is GuardResult.QUERY_REPLAY
                and not allow_replay
                and expected in (GuardReplyOpcode.KEEPALIVE, GuardReplyOpcode.STATUS)
            ):
                raise GuardSerialError(GuardSerialErrorCode.PROTOCOL)
            completion = (
                reply.opcode is GuardReplyOpcode.STATUS
                and reply.result is GuardResult.ACCEPTED
                and reply.state is GuardState.ARMED
                and reply.fault == 0
                and not reply.busy
            )
            if reply.opcode is expected:
                if (
                    expected in (GuardReplyOpcode.KEEPALIVE, GuardReplyOpcode.STATUS)
                    and sequence is not None
                    and reply.result in (GuardResult.ACCEPTED, GuardResult.QUERY_REPLAY)
                    and not (
                        expected is GuardReplyOpcode.STATUS
                        and reply.state
                        in (GuardState.BOOT, GuardState.DISARMED, GuardState.FAULT)
                    )
                ):
                    if reply.sequence < sequence:
                        continue
                    if reply.sequence > sequence:
                        raise GuardSerialError(GuardSerialErrorCode.STALE_REPLY)
                if completion and sequence is not None and reply.sequence < sequence:
                    continue
                return reply
            if (
                expected in (GuardReplyOpcode.KEEPALIVE, GuardReplyOpcode.STATUS)
                and reply.opcode
                in (GuardReplyOpcode.KEEPALIVE, GuardReplyOpcode.STATUS)
                and sequence is not None
                and reply.result in (GuardResult.ACCEPTED, GuardResult.QUERY_REPLAY)
                and reply.sequence < sequence
            ):
                continue
            if (
                expected not in (GuardReplyOpcode.KEEPALIVE, GuardReplyOpcode.STATUS)
                and reply.opcode
                in (GuardReplyOpcode.KEEPALIVE, GuardReplyOpcode.STATUS)
                and sequence is not None
                and reply.result in (GuardResult.ACCEPTED, GuardResult.QUERY_REPLAY)
            ):
                if reply.sequence < sequence:
                    continue
                raise GuardSerialError(GuardSerialErrorCode.STALE_REPLY)
            if expected is GuardReplyOpcode.STOP:
                continue
            if completion or (
                reply.opcode is GuardReplyOpcode.STOP
                and reply.result is GuardResult.ACCEPTED
                and reply.state is GuardState.FAULT
                and reply.fault == _STOP_FAULT_CODE
                and not reply.busy
            ):
                continue
            raise GuardSerialError(GuardSerialErrorCode.STALE_REPLY)

    async def _read_reply(self) -> GuardReply:
        while True:
            while self.receive_buffer and self.receive_buffer[0] != _FRAME_START:
                del self.receive_buffer[0]
            if len(self.receive_buffer) >= _FRAME_HEADER_LENGTH:
                frame_length = self.receive_buffer[1] + _FRAME_OVERHEAD
                if frame_length > _MAX_FRAME_LENGTH:
                    raise GuardSerialError(GuardSerialErrorCode.PROTOCOL)
                if len(self.receive_buffer) >= frame_length:
                    frame = bytes(self.receive_buffer[:frame_length])
                    del self.receive_buffer[:frame_length]
                    try:
                        return decode_reply(frame)
                    except GuardProtocolError as error:
                        raise GuardSerialError(GuardSerialErrorCode.PROTOCOL) from error
            try:
                chunk = await anyio.to_thread.run_sync(self.port.read, 64)
            except serial.SerialException as error:
                raise GuardSerialError(GuardSerialErrorCode.CONNECTION) from error
            if chunk:
                self.receive_buffer.extend(chunk)
            else:
                await anyio.sleep(_POLL_SECONDS)
