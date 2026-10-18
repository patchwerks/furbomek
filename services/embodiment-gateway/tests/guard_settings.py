from furbomek_gateway.guard_models import ActionName, GuardSettings


def powered_settings(
    path: str, actions: tuple[ActionName, ...] = ("active",)
) -> GuardSettings:
    return GuardSettings(
        bridge_device_path=path,
        mode="supervised_powered_bench",
        operator_profile="operator_present_supported_chassis",
        qualified_actions=actions,
        exchange_timeout_seconds=0.1,
        action_timeout_ms=500,
    )
