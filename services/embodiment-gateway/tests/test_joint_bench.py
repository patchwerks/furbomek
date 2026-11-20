import math

import pytest

from furbomek_gateway.guard_protocol import (
    GuardCommand,
    GuardProtocolError,
    encode_command,
)
from furbomek_gateway.guard_serial import GuardSerialTransport
from furbomek_gateway.joint_bench import (
    JointAngleError,
    JointProbe,
    arm_only_check,
    observed_travel,
    reference_stance,
    run_probe,
)
from tests.guard_settings import powered_settings
from tests.guard_support import PtyGuardBoard


@pytest.mark.anyio
async def test_probe_uses_separate_wire_family_and_verifies_disarm() -> None:
    probe = JointProbe(leg=6, axis="knee", direction="positive", degrees=30)
    with pytest.raises(GuardProtocolError):
        _ = encode_command(GuardCommand.EXEC, 2, action=probe.code)
    with PtyGuardBoard(supply_centivolts=805, strict_sequence=True) as board:
        port = await GuardSerialTransport.open(powered_settings(board.path))
        try:
            assert await arm_only_check(port)
            assert not board.actions
            assert await reference_stance(port)
            assert await run_probe(port, probe)
        finally:
            await port.aclose()
    assert board.actions == [0, 118]
    assert not board.stop_received.is_set()


@pytest.mark.anyio
async def test_probe_latches_stop_if_disarm_ack_is_wrong() -> None:
    probe = JointProbe(leg=1, axis="yaw", direction="negative", degrees=6)
    with PtyGuardBoard(
        supply_centivolts=805, resume_disarmed=True, bad_disarm_ack=True
    ) as board:
        port = await GuardSerialTransport.open(powered_settings(board.path))
        try:
            assert not await run_probe(port, probe)
        finally:
            await port.aclose()
    assert board.actions == [11]
    assert board.stop_received.is_set()


def test_joint_angles_are_measured_in_rectified_plane() -> None:
    before = ((-10.0, 0.0), (0.0, 0.0), (10.0, 0.0))
    unrectified_tip = (10.0 * math.sqrt(3) / 2, 10.0)
    distorted = (before[0], before[1], unrectified_tip)
    plane = (1.0, 0.0, 0.0, 0.0, 0.5, 0.0, 0.0, 0.0, 1.0)
    assert observed_travel(before, distorted, plane) == pytest.approx(30.0)
    with pytest.raises(JointAngleError):
        _ = observed_travel(
            before, distorted, (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        )
