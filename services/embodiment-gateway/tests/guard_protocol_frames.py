def _crc(data: bytes) -> int:
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


def reply(  # noqa: PLR0913, PLR0917
    opcode: int,
    result: int,
    state: int,
    sequence: int,
    value: int,
    busy: int,
    fault: int = 0,
) -> bytes:
    body = bytes(
        (
            opcode,
            result,
            state,
            sequence & 127,
            (sequence >> 7) & 127,
            (sequence >> 14) & 127,
            value & 127,
            value >> 7,
            fault,
            busy,
        )
    )
    checksum = _crc(bytes((len(body),)) + body)
    return bytes(
        (
            128,
            len(body),
            *body,
            checksum & 127,
            (checksum >> 7) & 127,
            checksum >> 14,
            129,
        )
    )
