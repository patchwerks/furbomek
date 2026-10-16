"""Pydantic models crossing the gateway and MCP trust boundaries."""

from enum import StrEnum
from ipaddress import IPv4Address
from typing import Annotated, ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field


class GatewaySettings(BaseModel):
    """Operator-local endpoint settings loaded from JSON."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    host: IPv4Address
    port: Annotated[int, Field(ge=1, le=65535)]
    timeout_seconds: Annotated[float, Field(gt=0, le=5)]


class MotionRequest(BaseModel):
    """Bounded semantic motion request that is evaluated but never sent."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    leg: Annotated[int, Field(ge=1, le=6)]
    delta_x: Annotated[int, Field(ge=-8, le=8)]
    delta_y: Annotated[int, Field(ge=-8, le=8)]
    delta_z: Annotated[int, Field(ge=-8, le=8)]
    duration_ms: Annotated[int, Field(ge=100, le=1000)]


class ResultStatus(StrEnum):
    """MCP operation connectivity state."""

    CONNECTED = "connected"
    UNAVAILABLE = "unavailable"


class ErrorCode(StrEnum):
    """Stable, non-sensitive tool failure codes."""

    CONNECTION_FAILED = "connection_failed"
    TIMEOUT = "timeout"
    INVALID_RESPONSE = "invalid_response"


class RobotStateResult(BaseModel):
    """Result of the exact stock echo request."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    status: ResultStatus
    connected: bool
    stock_echo_validated: bool
    motor_power_known: bool
    joint_positions_known: bool
    stop_capability_qualified: bool
    error_code: ErrorCode | None = None


class SupplyVoltageResult(BaseModel):
    """Controller-reported voltage result with explicit interpretation limits."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    status: ResultStatus
    connected: bool
    controller_reported_voltage_volts: float | None = None
    interpretation: (
        Literal["controller_reported_not_calibrated_or_independent_power_safety"] | None
    ) = None
    error_code: ErrorCode | None = None


class CapabilitiesResult(BaseModel):
    """Factual stock protocol and current backend capability boundary."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    stock_per_leg_protocol_available: bool
    stock_gait_protocol_available: bool
    preemptive_stop_qualified: bool
    local_ttl_watchdog_qualified: bool
    current_backend_readonly: bool
    actuator_commands_targeted: bool
    unresolved_faults: tuple[Literal["rear_right_leg"], ...]


class MotionRequestResult(BaseModel):
    """Explicit policy result for a motion request."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    decision: Literal["rejected"]
    reason: Literal["local_safety_unqualified"]
    sent: Literal[False]
    network_accessed: Literal[False]
