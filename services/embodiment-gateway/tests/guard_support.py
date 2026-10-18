import threading
from dataclasses import dataclass, field
from typing import override

from tests.guard_protocol_frames import reply as _reply
from tests.guard_pty_link import PtyLink


@dataclass(slots=True)
class PtyGuardBoard(PtyLink):
    supply_centivolts: int = 200
    arm_result: int = 0
    hang_replies: bool = False
    auto_complete: bool = True
    unsolicited_completion: bool = False
    fault_on_completion: bool = False
    stop_reply_copies: int = 1
    disconnect_on_stop: bool = False
    partial_supply: bool = False
    resume_disarmed: bool = False
    strict_sequence: bool = False
    disarm_result: int = 0
    bad_disarm_ack: bool = False
    wrong_disarm_sequence: bool = False
    initial_state: int = 0
    hold_begin_reply: bool = False
    hold_status_reply: bool = False
    drop_first_keep_reply: bool = False
    drop_keep_replies: int = 0
    keep_reply_copies: int = 1
    complete_after_keep_count: int = 0
    query_remaining_ms: int = 500
    partial_sent: threading.Event = field(default_factory=threading.Event)
    release_supply: threading.Event = field(default_factory=threading.Event)
    executed: threading.Event = field(default_factory=threading.Event)
    heartbeat_received: threading.Event = field(default_factory=threading.Event)
    stop_received: threading.Event = field(default_factory=threading.Event)
    received: list[bytes] = field(default_factory=list)
    actions: list[int] = field(default_factory=list)
    begin_received: threading.Event = field(default_factory=threading.Event)
    status_received: threading.Event = field(default_factory=threading.Event)
    _state: int = field(init=False, default=0)
    _sequence: int = field(init=False, default=0)
    _busy: bool = field(init=False, default=False)
    _keep_count: int = field(init=False, default=0)

    @override
    def _before_start(self) -> None:
        self._state = self.initial_state
        if self.resume_disarmed:
            self._state = 5
            self._sequence = 20

    def _receive_stop(self) -> None:
        self.received.append(b"\x80\x30\x81")
        self._state, self._busy = 4, False
        self.stop_received.set()
        if self.disconnect_on_stop:
            self._disconnect_from_worker()
            return
        if not self.hang_replies:
            for _ in range(self.stop_reply_copies):
                self._write(_reply(0x31, 0, 4, self._sequence, 0, 0, fault=4))

    def _supply_reply(self) -> None:
        response = _reply(
            0x35, 0, self._state, self._sequence, self.supply_centivolts, 0
        )
        if self.partial_supply:
            self._write(response[:8])
            self.partial_sent.set()
            _ = self.release_supply.wait(timeout=1)
            self._write(response[8:])
        else:
            self._write(response)

    @override
    def _consume(self, buffer: bytearray) -> None:  # noqa: C901, PLR0912, PLR0915
        while True:
            if buffer.startswith(b"\x80\x30\x81"):
                del buffer[:3]
                self._receive_stop()
                if self._disconnected:
                    return
                continue
            if len(buffer) < 2 or buffer[0] != 128:
                return
            total = buffer[1] + 6
            if len(buffer) < total:
                return
            frame = bytes(buffer[:total])
            del buffer[:total]
            self.received.append(frame)
            if self.hang_replies:
                continue
            opcode, sequence = frame[2], frame[3] | frame[4] << 7 | frame[5] << 14
            if opcode == 0x34:
                self._supply_reply()
            elif opcode == 0x28:
                self.begin_received.set()
                expected = 0 if self._state == 0 else self._sequence + 1
                if self.strict_sequence and sequence != expected:
                    self._write(_reply(0x29, 4, self._state, self._sequence, 0, 0))
                else:
                    self._state, self._sequence = 1, sequence
                    if self.hold_begin_reply:
                        continue
                    self._write(_reply(0x29, 0, 1, sequence, 500, 0))
            elif opcode == 0x2A:
                if self.strict_sequence and sequence != self._sequence + 1:
                    self._write(_reply(0x2B, 4, self._state, self._sequence, 0, 0))
                    continue
                if self.arm_result == 0:
                    self._state, self._sequence = 3, sequence
                self._write(
                    _reply(0x2B, self.arm_result, self._state, self._sequence, 500, 0)
                )
            elif opcode == 0x2E:
                if self.strict_sequence and sequence != self._sequence + 1:
                    self._write(_reply(0x2F, 4, self._state, self._sequence, 0, 0))
                    continue
                self._sequence, self._busy = sequence, True
                self.actions.append(frame[6])
                self._write(_reply(0x2F, 0, self._state, sequence, 500, 1))
                self.executed.set()
            elif opcode == 0x32:
                self.status_received.set()
                status_sync = self._state == 5 and sequence == 0
                duplicate = (
                    self._state not in (0, 4)
                    and sequence == self._sequence
                    and not status_sync
                )
                if self.strict_sequence and not (
                    self._state in (0, 4)
                    or status_sync
                    or duplicate
                    or sequence == self._sequence + 1
                ):
                    self._write(_reply(0x33, 4, self._state, self._sequence, 0, 0))
                    continue
                if self._state not in (0, 4, 5) and not status_sync:
                    self._sequence = sequence
                if self.hold_status_reply:
                    continue
                was_busy = self._busy
                if self.auto_complete:
                    self._busy = False
                if self.fault_on_completion and was_busy:
                    self._state, self._busy, was_busy = 4, False, False
                self._write(
                    _reply(
                        0x33,
                        10 if duplicate else 0,
                        self._state,
                        self._sequence,
                        500,
                        int(was_busy),
                    )
                )
            elif opcode == 0x2C:
                duplicate = sequence == self._sequence
                if (
                    self.strict_sequence
                    and not duplicate
                    and sequence != self._sequence + 1
                ):
                    self._write(_reply(0x2D, 4, self._state, self._sequence, 0, 0))
                    continue
                self._keep_count += 1
                if not duplicate:
                    self._sequence = sequence
                if self.fault_on_completion and self._busy:
                    self._state, self._busy = 4, False
                elif (
                    (self.unsolicited_completion and self._busy)
                    or self.auto_complete
                    or (
                        self.complete_after_keep_count > 0
                        and self._keep_count >= self.complete_after_keep_count
                    )
                ):
                    self._busy = False
                self.heartbeat_received.set()
                if self.drop_first_keep_reply and self._keep_count == 1:
                    continue
                if self.drop_keep_replies > 0:
                    self.drop_keep_replies -= 1
                    continue
                for _ in range(self.keep_reply_copies):
                    self._write(
                        _reply(
                            0x2D,
                            10 if duplicate else 0,
                            self._state,
                            self._sequence,
                            self.query_remaining_ms,
                            int(self._busy),
                        )
                    )
            elif opcode == 0x36:
                if self.strict_sequence and sequence != self._sequence + 1:
                    self._write(_reply(0x37, 4, self._state, self._sequence, 0, 0))
                    continue
                self._sequence = sequence
                state = 3 if self.bad_disarm_ack else 5
                fault = 1 if self.bad_disarm_ack else 0
                self._write(
                    _reply(
                        0x37,
                        self.disarm_result,
                        state,
                        sequence + 1 if self.wrong_disarm_sequence else sequence,
                        0,
                        0,
                        fault=fault,
                    )
                )
                if self.disarm_result == 0 and not self.bad_disarm_ack:
                    self._state, self._busy = 5, False
            else:
                self._sequence = sequence
                self._write(_reply(opcode + 1, 0, self._state, sequence, 500, 0))
