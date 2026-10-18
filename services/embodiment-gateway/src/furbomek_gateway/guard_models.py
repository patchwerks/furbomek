"""Closed configuration and result models for the motor-off guard adapter."""

from typing import Annotated, ClassVar, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

type ActionName = Literal[
    "active",
    "sleep",
    "forward",
    "backward",
    "left",
    "right",
    "turn_left",
    "turn_right",
]
type PoweredActionDecision = Literal["completed", "refused", "unavailable"]
type PoweredActionReason = Literal[
    "completed_and_disarmed",
    "mode_not_qualified",
    "action_not_qualified",
    "supply_gate_failed",
    "guard_not_ready",
    "protocol_rejected",
    "operation_timeout",
    "transport_failure",
    "cancelled",
    "disarm_rejected",
    "stop_fault",
]


class _GuardSettingsContractError(ValueError):
    pass


class GuardSettings(BaseModel):
    """Private fixed-path configuration for the separate guarded UART server."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    bridge_device_path: Annotated[str, Field(min_length=1)]
    mode: Literal["motor_off_bench", "supervised_powered_bench"]
    operator_profile: Literal[
        "operator_confirmed_motor_off_bench", "operator_present_supported_chassis"
    ]
    exchange_timeout_seconds: Annotated[float, Field(gt=0, le=0.20)] = 0.20
    active_check_timeout_ms: Annotated[int, Field(gt=0, le=2000)] = 2000
    action_timeout_ms: Annotated[int, Field(gt=0, le=2500)] = 2500
    qualified_actions: tuple[ActionName, ...] = ("active",)
    automatic_robot_reset_enabled: Literal[False] = False

    @model_validator(mode="after")
    def validate_operator_profile(self) -> Self:
        """Require the operator profile that belongs to the selected mode."""
        if self.mode == "motor_off_bench":
            valid_profile = (
                self.operator_profile == "operator_confirmed_motor_off_bench"
            )
        else:
            valid_profile = (
                self.operator_profile == "operator_present_supported_chassis"
            )
        if not valid_profile:
            raise _GuardSettingsContractError
        if len(self.qualified_actions) != len(set(self.qualified_actions)):
            raise _GuardSettingsContractError
        return self


class GuardAvailabilityResult(BaseModel):
    """Base factual availability claims shared by guard tool results."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    available: bool
    physical_motor_state: Literal["unknown"] = "unknown"
    physical_motion_observed: Literal[False] = False
    watchdog_enabled_by_guard_configuration: Literal[True] = True
    watchdog_reset_behavior_tested: Literal[False] = False
    automatic_robot_reset_enabled: Literal[False] = False


class GuardStateResult(GuardAvailabilityResult):
    """Observed Guard reply state without physical-motion inference."""

    guard_state: (
        Literal["boot", "session", "arming", "armed", "disarmed", "fault"] | None
    )
    busy: bool | None
    fault_code: int | None
    physical_reset_required: bool | None
    error_code: str | None = None


class GuardSupplyVoltageResult(GuardAvailabilityResult):
    """Guard-reported supply read with its conservative interpretation limit."""

    supply_voltage_volts: float | None
    interpretation: Literal["not_independent_motor_power_proof"]
    error_code: str | None = None


class GuardCapabilitiesResult(GuardAvailabilityResult):
    """Static adapter scope and protocol capabilities."""

    guarded_uart_protocol_available: Literal[True] = True
    read_only_supply_available: Literal[True] = True
    raw_stop_available: Literal[True] = True
    one_bounded_active_check_available: bool
    powered_semantic_action_available: bool
    configured_mode: Literal["motor_off_bench", "supervised_powered_bench"]
    operator_profile: Literal[
        "operator_confirmed_motor_off_bench", "operator_present_supported_chassis"
    ]
    qualified_actions: tuple[ActionName, ...]


class GuardStopResult(GuardAvailabilityResult):
    """Protocol-level STOP delivery result without physical-stop claims."""

    stop_frame_sent: bool
    fault_verified: bool
    physical_reset_required: bool | None
    error_code: str | None = None


class MotorOffCheckResult(GuardAvailabilityResult):
    """Bounded Active protocol outcome on the explicitly motor-off bench mode."""

    decision: Literal["completed", "refused", "unavailable"]
    reason: Literal[
        "completed_without_physical_observation",
        "mode_not_qualified",
        "supply_gate_failed",
        "guard_not_boot",
        "protocol_rejected",
        "operation_timeout",
        "transport_failure",
        "cancelled",
    ]
    supply_voltage_volts: float | None
    active_accepted: bool
    busy_cleared: bool
    stop_frame_sent: bool
    fault_verified: bool
    physical_reset_required: bool | None
    lease_lower_bound_ms: int | None = None


class PoweredActionResult(GuardAvailabilityResult):
    """Bounded semantic action facts without physical-health inference."""

    action: ActionName
    decision: PoweredActionDecision
    reason: PoweredActionReason
    supply_voltage_volts: float | None
    action_accepted: bool
    action_completed: bool
    disarm_acknowledged: bool
    stop_frame_sent: bool
    fault_verified: bool
    physical_reset_required: bool | None
    lease_lower_bound_ms: int | None = None
    error_code: str | None = None
