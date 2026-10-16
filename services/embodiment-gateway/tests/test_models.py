from ipaddress import IPv4Address

from furbomek_gateway.models import GatewaySettings, MotionRequest


def test_motion_request_is_bounded() -> None:
    request = MotionRequest(
        leg=1,
        delta_x=8,
        delta_y=-8,
        delta_z=0,
        duration_ms=1000,
    )

    assert request.leg == 1
    assert request.delta_x == 8
    assert request.duration_ms == 1000


def test_settings_require_an_ipv4_endpoint() -> None:
    settings = GatewaySettings(
        host=IPv4Address("127.0.0.1"),
        port=65535,
        timeout_seconds=1.0,
    )

    assert str(settings.host) == "127.0.0.1"
    assert settings.port == 65535
