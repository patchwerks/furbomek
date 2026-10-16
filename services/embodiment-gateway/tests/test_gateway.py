from ipaddress import IPv4Address

import pytest
from pydantic import ValidationError

from furbomek_gateway.gateway import GatewayService
from furbomek_gateway.models import GatewaySettings, MotionRequest
from furbomek_gateway.transport import StockTcpTransport


def test_settings_reject_extra_fields() -> None:
    with pytest.raises(ValidationError) as raised:
        _ = GatewaySettings.model_validate(
            {
                "host": "127.0.0.1",
                "port": 65535,
                "timeout_seconds": 1,
                "credential": "not-accepted",
            }
        )

    assert raised.value.errors()[0]["type"] == "extra_forbidden"


@pytest.mark.parametrize(
    ("field", "value"),
    [("port", 0), ("port", 65536), ("timeout_seconds", 0), ("timeout_seconds", 5.1)],
)
def test_settings_reject_out_of_range_values(field: str, value: float) -> None:
    payload = {
        "host": "127.0.0.1",
        "port": 65535,
        "timeout_seconds": 1.0,
        field: value,
    }

    with pytest.raises(ValidationError) as raised:
        _ = GatewaySettings.model_validate(payload)

    assert raised.value.errors()[0]["loc"] == (field,)


def test_motion_request_rejects_out_of_bounds_values() -> None:
    with pytest.raises(ValidationError) as raised:
        _ = MotionRequest(
            leg=7,
            delta_x=0,
            delta_y=0,
            delta_z=0,
            duration_ms=100,
        )

    assert raised.value.errors()[0]["loc"] == ("leg",)


def test_motion_policy_does_not_access_network() -> None:
    settings = GatewaySettings(
        host=IPv4Address("127.0.0.1"),
        port=1,
        timeout_seconds=0.1,
    )
    service = GatewayService(StockTcpTransport(settings))
    request = MotionRequest(
        leg=1,
        delta_x=0,
        delta_y=0,
        delta_z=0,
        duration_ms=100,
    )

    result = service.request_motion(request)

    assert result.model_dump() == {
        "decision": "rejected",
        "reason": "local_safety_unqualified",
        "sent": False,
        "network_accessed": False,
    }


def test_capabilities_preserve_unqualified_safety_boundary() -> None:
    settings = GatewaySettings(
        host=IPv4Address("127.0.0.1"),
        port=65535,
        timeout_seconds=1,
    )
    service = GatewayService(StockTcpTransport(settings))

    result = service.get_capabilities()

    assert result.stock_per_leg_protocol_available is True
    assert result.stock_gait_protocol_available is True
    assert result.preemptive_stop_qualified is False
    assert result.local_ttl_watchdog_qualified is False
    assert result.current_backend_readonly is True
    assert result.actuator_commands_targeted is False
    assert result.unresolved_faults == ("rear_right_leg",)
