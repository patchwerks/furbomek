import pytest

from furbomek_gateway.guard_gateway import GuardService
from tests.guard_settings import powered_settings
from tests.guard_support import PtyGuardBoard


@pytest.mark.anyio
async def test_poll_sleep_is_included_in_remaining_lease_requirement() -> None:
    with PtyGuardBoard(
        supply_centivolts=800,
        strict_sequence=True,
        auto_complete=False,
        query_remaining_ms=190,
    ) as board:
        service = GuardService(powered_settings(board.path))
        await service.open()
        try:
            result = await service.perform_action("active")
        finally:
            await service.aclose()
    heartbeats = [
        frame for frame in board.received if len(frame) > 3 and frame[2] == 0x2C
    ]
    assert len(heartbeats) == 1
    assert result.decision != "completed"
    assert result.stop_frame_sent
    assert not result.disarm_acknowledged
