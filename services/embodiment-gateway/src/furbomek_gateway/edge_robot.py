"""Local admission and expiry for the existing guarded robot service."""

import time
from typing import Final, final

import anyio

from furbomek_gateway.edge_protocol import EdgeReply, OperatorCommand, RobotRequest
from furbomek_gateway.guard_gateway import GuardService
from furbomek_gateway.guard_models import GuardSettings, GuardStateResult
from furbomek_gateway.guard_serial_errors import GuardSerialError

PREPARATION_SECONDS: Final = 600
BENCH_SECONDS: Final = 120
HANDHELD_BOOT_SECONDS: Final = 2
OFF_GATE_VOLTS: Final = 3.0
POWERED_MIN_VOLTS: Final = 6.5
POWERED_MAX_VOLTS: Final = 8.6
SAFE_IDLE_STATES: Final = ("boot", "disarmed")


def _healthy_idle(state: GuardStateResult) -> bool:
    return (
        state.available
        and state.guard_state in SAFE_IDLE_STATES
        and state.busy is False
        and state.fault_code == 0
    )


@final
class RobotBench:
    """Hold one bridge only after local physical confirmation."""

    def __init__(self, settings: GuardSettings) -> None:
        """Initialize with both serial access and powered motion closed."""
        self.settings = settings
        self._guard: GuardService | None = None
        self._lock = anyio.Lock()
        self._expires = 0.0
        self._monotonic_expiry = 0.0
        self._powered = False
        self._tunnel_up = False
        self._stop_generation = 0

    async def tunnel_changed(self, *, connected: bool) -> None:
        """End bench authority when the reverse SSH transport exits."""
        async with self._lock:
            self._tunnel_up = connected
            if not connected:
                await self._close()

    async def expire(self) -> None:
        """Release the port when the local operator window ends."""
        async with self._lock:
            if self._guard is not None and not self._within_window():
                await self._close()

    def _within_window(self) -> bool:
        return time.time() < self._expires and time.monotonic() < self._monotonic_expiry

    def _set_window(self, seconds: int) -> None:
        self._expires = time.time() + seconds
        self._monotonic_expiry = time.monotonic() + seconds

    async def _close(self) -> None:
        guard, self._guard = self._guard, None
        self._powered = False
        self._expires = 0
        self._monotonic_expiry = 0
        if guard is not None:
            await guard.aclose()

    async def operator(self, command: OperatorCommand) -> EdgeReply:
        """Serve only the distinct non-forwarded operator socket."""
        async with self._lock:
            match command:
                case "close":
                    await self._close()
                    return EdgeReply(result="ok", state="bench_closed")
                case "prepare":
                    return await self._prepare()
                case "enable":
                    return await self._enable()

    async def _prepare(self) -> EdgeReply:
        if not self._tunnel_up or self._guard is not None:
            return EdgeReply(
                result="refused", state="tunnel_required_and_bench_must_be_closed"
            )
        candidate = GuardService(self.settings)
        admitted = False
        try:
            await candidate.open()
            await anyio.sleep(HANDHELD_BOOT_SECONDS)
            state = await candidate.get_state()
            supply = await candidate.get_supply_voltage()
            voltage = supply.supply_voltage_volts
            if not _healthy_idle(state) or not supply.available or voltage is None:
                return EdgeReply(
                    result="unavailable", state="no_healthy_idle_guard", robot=state
                )
            if not 0 <= voltage < OFF_GATE_VOLTS:
                return EdgeReply(result="refused", state="power_off_gate", robot=supply)
            self._guard = candidate
            self._set_window(PREPARATION_SECONDS)
            admitted = True
            return EdgeReply(result="ok", state="prepared_read_only", robot=state)
        except GuardSerialError:
            return EdgeReply(result="unavailable", state="bridge_open_failed")
        finally:
            if not admitted:
                await candidate.aclose()

    async def _enable(self) -> EdgeReply:
        guard = self._guard
        if (
            not self._tunnel_up
            or guard is None
            or self._powered
            or not self._within_window()
        ):
            return EdgeReply(result="refused", state="fresh_local_preparation_required")
        generation = self._stop_generation
        state = await guard.get_state()
        supply = await guard.get_supply_voltage()
        voltage = supply.supply_voltage_volts
        if not _healthy_idle(state) or not supply.available or voltage is None:
            return EdgeReply(
                result="unavailable", state="no_healthy_idle_guard", robot=state
            )
        if not POWERED_MIN_VOLTS <= voltage <= POWERED_MAX_VOLTS:
            return EdgeReply(
                result="refused", state="powered_supply_gate", robot=supply
            )
        if not await guard.verify_bench_arm() or generation != self._stop_generation:
            return EdgeReply(result="refused", state="arm_only_verification_failed")
        self._powered = True
        self._set_window(BENCH_SECONDS)
        return EdgeReply(
            result="ok", state="operator_present_bench_enabled", robot=supply
        )

    async def remote(self, request: RobotRequest) -> EdgeReply:
        """Preserve STOP priority and the original guard's action semantics."""
        guard = self._guard
        if guard is None:
            return EdgeReply(result="refused", state="local_bench_closed")
        if request.command == "stop":
            self._stop_generation += 1
            self._powered = False
            stopped = await guard.stop()
            result = "ok" if stopped.fault_verified else "unavailable"
            return EdgeReply(result=result, state="terminal_stop", robot=stopped)
        if not self._tunnel_up or not self._within_window():
            return EdgeReply(result="refused", state="bench_expired_or_disconnected")
        match request.command:
            case "state":
                report = await guard.get_state()
                label = "guard_status"
            case "voltage":
                report = await guard.get_supply_voltage()
                label = "guard_voltage"
            case "capabilities":
                report = guard.get_capabilities()
                label = "powered_bench" if self._powered else "read_only_bench"
            case action:
                if not self._powered:
                    return EdgeReply(
                        result="refused", state="local_powered_bench_required"
                    )
                outcome = await guard.perform_action(action)
                if not outcome.disarm_acknowledged:
                    self._powered = False
                return EdgeReply(
                    result="ok" if outcome.disarm_acknowledged else "refused",
                    state=outcome.reason,
                    robot=outcome,
                )
        return EdgeReply(
            result="ok" if report.available else "unavailable",
            state=label,
            robot=report,
        )
