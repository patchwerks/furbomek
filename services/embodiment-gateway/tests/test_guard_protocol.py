import pytest

from furbomek_gateway.guard_protocol import (
    GuardCommand,
    GuardProtocolError,
    GuardProtocolErrorCode,
    decode_reply,
    encode_begin,
    encode_command,
)
from furbomek_gateway.guard_serial import lease_lower_bound


def test_begin_encodes_fresh_eight_byte_correlation_as_a_guard_frame() -> None:
    # Given: an eight-byte CSPRNG correlation value.
    correlation = bytes(range(8))

    # When: BEGIN is encoded.
    frame = encode_begin(correlation)

    # Then: it matches the independent guard frame grammar and fixed body length.
    assert frame == bytes.fromhex(
        "80 14 28 00 00 00 00 00 01 00 02 00 03 00 04 00 05 00 06 00 07 00 16 17 02 81"
    )


def test_exec_active_encodes_only_action_zero_and_a_strict_sequence() -> None:
    # Given: the first usable guarded sequence.
    sequence = 1

    # When: Active EXEC is encoded.
    frame = encode_command(GuardCommand.EXEC, sequence, action=0)

    # Then: the wire frame carries only the bounded action.
    assert frame == bytes.fromhex("80 05 2e 01 00 00 00 39 79 03 81")


def test_disarm_encodes_as_a_sequenced_four_byte_command() -> None:
    frame = encode_command(GuardCommand.DISARM, 7)

    assert frame[1] == 4
    assert frame[2:6] == bytes((0x36, 7, 0, 0))


def test_disarm_reply_rejects_body_four_without_sequence() -> None:
    frame = _frame(bytes((0x37, 0, 5, 0)))

    with pytest.raises(GuardProtocolError) as raised:
        _ = decode_reply(frame)

    assert raised.value.code is GuardProtocolErrorCode.FRAME


def test_query_replay_marker_is_only_valid_for_keep_or_status() -> None:
    frame = _frame(bytes((0x2B, 10, 3, 0, 0, 0, 0, 0, 0, 0)))

    with pytest.raises(GuardProtocolError) as raised:
        _ = decode_reply(frame)

    assert raised.value.code is GuardProtocolErrorCode.RESULT


def test_lease_lower_bound_rounds_elapsed_time_up_and_keeps_margin() -> None:
    assert lease_lower_bound(100, 0.0301) == 59
    assert lease_lower_bound(100, 0.0901) == 0


def test_supply_reply_interprets_bytes_eight_and_nine_as_centivolts() -> None:
    # Given: a valid 0x35 standard reply with 2.55 V in bytes eight and nine.
    frame = bytes.fromhex("80 0a 35 00 00 00 00 00 7f 01 00 00 72 30 00 81")

    # When: the guarded reply is decoded.
    reply = decode_reply(frame)

    # Then: supply semantics do not reuse the normal remaining-milliseconds field.
    assert reply.supply_voltage_volts == 2.55
    assert reply.remaining_ms is None
    assert reply.sequence == 0


def _frame(body: bytes) -> bytes:
    value = 0xFFFF
    for byte in bytes((len(body),)) + body:
        value ^= byte << 8
        for _ in range(8):
            value = (
                ((value << 1) ^ 0x1021) & 0xFFFF
                if value & 0x8000
                else (value << 1) & 0xFFFF
            )
    return bytes(
        (
            0x80,
            len(body),
            *body,
            value & 0x7F,
            (value >> 7) & 0x7F,
            value >> 14,
            0x81,
        )
    )


@pytest.mark.parametrize(
    ("frame", "code"),
    [
        (
            bytes.fromhex("80 0a 34 00 00 00 00 00 00 00 00 00 1c 2d 03 81"),
            GuardProtocolErrorCode.OPCODE,
        ),
        (
            bytes.fromhex("80 0a 35 00 00 00 00 00 00 00 00 00 58 73 02 81"),
            GuardProtocolErrorCode.CRC,
        ),
        (
            bytes.fromhex("80 0a 35 00 00 00 00 00 00 00 00 00 00 00 00"),
            GuardProtocolErrorCode.TRUNCATED,
        ),
    ],
)
def test_reply_decoder_rejects_invalid_guard_wire_data(
    frame: bytes, code: GuardProtocolErrorCode
) -> None:
    # Given: a malformed, stale, or truncated guarded reply.

    # When: the boundary parser receives it.
    with pytest.raises(GuardProtocolError) as raised:
        _ = decode_reply(frame)

    # Then: no untrusted frame becomes a reply model.
    assert raised.value.code is code
