import pytest
from pydantic import ValidationError

from furbomek_gateway.guard_models import GuardSettings


def test_guard_settings_accept_only_motor_off_bench_profile() -> None:
    # Given: a private, fixed bridge configuration.
    settings = GuardSettings(
        bridge_device_path="/dev/pts/9",
        mode="motor_off_bench",
        operator_profile="operator_confirmed_motor_off_bench",
        exchange_timeout_seconds=0.2,
        active_check_timeout_ms=2000,
    )

    # When: the validated settings are consumed.
    payload = settings.model_dump()

    # Then: automatic reset is structurally disabled.
    assert payload["automatic_robot_reset_enabled"] is False


def test_guard_settings_default_powered_allowlist_is_active_only() -> None:
    settings = GuardSettings(
        bridge_device_path="/dev/pts/9",
        mode="supervised_powered_bench",
        operator_profile="operator_present_supported_chassis",
    )

    assert settings.qualified_actions == ("active",)
    assert settings.action_timeout_ms == 2500


def test_guard_settings_accepts_explicit_powered_action_allowlist() -> None:
    settings = GuardSettings(
        bridge_device_path="/dev/pts/9",
        mode="supervised_powered_bench",
        operator_profile="operator_present_supported_chassis",
        qualified_actions=("active", "forward"),
    )

    assert settings.qualified_actions == ("active", "forward")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("exchange_timeout_seconds", 0),
        ("exchange_timeout_seconds", 0.201),
        ("exchange_timeout_seconds", 0.35),
        ("active_check_timeout_ms", 0),
        ("active_check_timeout_ms", 2001),
        ("mode", "production"),
    ],
)
def test_guard_settings_reject_unsafe_or_out_of_contract_values(
    field: str, value: float | str
) -> None:
    # Given: a valid guard settings payload with one unsafe replacement.
    payload = {
        "bridge_device_path": "/dev/pts/9",
        "mode": "motor_off_bench",
        "operator_profile": "operator_confirmed_motor_off_bench",
        "exchange_timeout_seconds": 0.2,
        "active_check_timeout_ms": 1000,
        field: value,
    }

    # When: settings parsing is attempted.
    with pytest.raises(ValidationError) as raised:
        _ = GuardSettings.model_validate(payload)

    # Then: the unsafe field is rejected at the boundary.
    assert raised.value.errors()[0]["loc"] == (field,)
