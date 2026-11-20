"""Local admission and expiry for the existing guarded robot service."""

from collections.abc import Callable
from time import monotonic, time
from typing import Final, Literal, assert_never, final

import anyio

from furbomek_gateway.edge_protocol import EdgeReply, OperatorCommand, RobotRequest
from furbomek_gateway.guard_gateway import GuardService
from furbomek_gateway.guard_models import ActionName, GuardSettings, GuardStateResult
from furbomek_gateway.guard_serial_errors import GuardSerialError, GuardSerialErrorCode

BENCH_SECONDS: Final = 120
MOTION_REQUEST_SECONDS: Final = 8.0
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
    """Own the bridge independently of short, locally enabled motion windows."""

    def __init__(
        self,
        settings: GuardSettings,
        observation_ready: Callable[[], bool] | None = None,
    ) -> None:
        """Initialize with both serial access and powered motion closed."""
        self.settings = settings
        self._observation_ready = observation_ready
        self._guard: GuardService | None = None
        self._lock = anyio.Lock()
        self._request_gate = anyio.Lock()
        self._active_motion: anyio.CancelScope | None = None
        self._expires = 0.0
        self._monotonic_expiry = 0.0
        self._tunnel_up = False
        self._stop_generation = 0

    def tunnel_changed(self, *, connected: bool) -> None:
        """Revoke motion when reverse SSH disconnects, retaining the bridge."""
        self._tunnel_up = connected
        if not connected:
            self._hold_motion()

    def expire(self) -> None:
        """End a powered window after expiry or required tracking loss."""
        if self._expires and (self._remaining() <= 0 or not self._can_observe()):
            self._hold_motion()

    def _can_observe(self) -> bool:
        return self._observation_ready is None or self._observation_ready()

    def _remaining(self) -> float:
        return min(self._expires - time(), self._monotonic_expiry - monotonic())

    def _hold_motion(self) -> None:
        self._stop_generation += 1
        self._expires = 0.0
        self._monotonic_expiry = 0.0
        if self._active_motion is not None:
            self._active_motion.cancel()

    async def _close(self) -> None:
        self._hold_motion()
        guard, self._guard = self._guard, None
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
            assert_never(command)

    async def _prepare(self) -> EdgeReply:
        if self._guard is not None:
            return EdgeReply(result="refused", state="bridge_already_prepared")
        candidate = GuardService(self.settings)
        admitted = False
        try:
            await candidate.open()
            await anyio.sleep(HANDHELD_BOOT_SECONDS)
            state = await candidate.get_state()
            supply = await candidate.get_supply_voltage()
            voltage = supply.supply_voltage_volts
            if (
                state.error_code == GuardSerialErrorCode.TIMEOUT
                and supply.error_code == GuardSerialErrorCode.TIMEOUT
            ):
                reply = EdgeReply(result="ok", state="prepared_waiting_for_robot")
            elif not _healthy_idle(state) or not supply.available or voltage is None:
                return EdgeReply(
                    result="unavailable", state="no_healthy_idle_guard", robot=state
                )
            elif not 0 <= voltage < OFF_GATE_VOLTS:
                return EdgeReply(result="refused", state="power_off_gate", robot=supply)
            else:
                reply = EdgeReply(result="ok", state="prepared_read_only", robot=state)
        except GuardSerialError:
            return EdgeReply(result="unavailable", state="bridge_open_failed")
        else:
            self._guard = candidate
            admitted = True
            return reply
        finally:
            if not admitted:
                await candidate.aclose()

    async def _enable(self) -> EdgeReply:
        guard = self._guard
        if not self._tunnel_up or guard is None:
            return EdgeReply(result="refused", state="fresh_local_preparation_required")
        if self._remaining() > 0 or self._active_motion is not None:
            return EdgeReply(result="refused", state="bench_already_enabled_or_busy")
        if not self._can_observe():
            return EdgeReply(result="refused", state="fresh_robot_tracking_required")
        return await self._verify_and_enable(guard)

    async def _verify_and_enable(self, guard: GuardService) -> EdgeReply:
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
        if generation != self._stop_generation or not self._can_observe():
            return EdgeReply(result="refused", state="bench_admission_interrupted")
        if not await guard.verify_bench_arm():
            return EdgeReply(result="refused", state="arm_only_verification_failed")
        if generation != self._stop_generation or not self._can_observe():
            return EdgeReply(result="refused", state="bench_admission_interrupted")
        self._expires = time() + BENCH_SECONDS
        self._monotonic_expiry = monotonic() + BENCH_SECONDS
        return EdgeReply(
            result="ok", state="operator_present_bench_enabled", robot=supply
        )

    async def remote(self, request: RobotRequest) -> EdgeReply:
        """Preserve STOP priority and reject competing requests without queuing."""
        guard = self._guard
        if guard is None:
            return EdgeReply(result="refused", state="local_bench_closed")
        command = request.command
        if command == "stop":
            self._hold_motion()
            stopped = await guard.stop()
            result = "ok" if stopped.fault_verified else "unavailable"
            return EdgeReply(result=result, state="terminal_stop", robot=stopped)
        if not self._tunnel_up:
            return EdgeReply(result="refused", state="bench_disconnected")
        self.expire()
        if command == "capabilities":
            report = guard.get_capabilities()
            in_window = self._remaining() >= MOTION_REQUEST_SECONDS
            label = "powered_bench" if in_window else "read_only_bench"
            if not in_window:
                report = report.model_copy(
                    update={"powered_semantic_action_available": False}
                )
            return EdgeReply(result="ok", state=label, robot=report)
        try:
            self._request_gate.acquire_nowait()
        except anyio.WouldBlock:
            return EdgeReply(result="refused", state="robot_request_busy")
        try:
            return await self._dispatch(guard, command)
        finally:
            self._request_gate.release()

    async def _dispatch(
        self, guard: GuardService, command: ActionName | Literal["state", "voltage"]
    ) -> EdgeReply:
        match command:
            case "state":
                state = await guard.get_state()
                if not _healthy_idle(state):
                    self._hold_motion()
                return EdgeReply(
                    result="ok" if state.available else "unavailable",
                    state="guard_status",
                    robot=state,
                )
            case "voltage":
                supply = await guard.get_supply_voltage()
                if not supply.available:
                    self._hold_motion()
                return EdgeReply(
                    result="ok" if supply.available else "unavailable",
                    state="guard_voltage",
                    robot=supply,
                )
            case action:
                return await self._perform_action(guard, action)

    async def _perform_action(
        self, guard: GuardService, action: ActionName
    ) -> EdgeReply:
        remaining = self._remaining()
        if remaining <= 0:
            return EdgeReply(result="refused", state="local_powered_bench_required")
        if remaining < MOTION_REQUEST_SECONDS:
            return EdgeReply(result="refused", state="motion_window_budget")
        completed = False
        outcome = None
        with anyio.move_on_after(MOTION_REQUEST_SECONDS) as motion:
            self._active_motion = motion
            try:
                outcome = await guard.perform_action(action, require_disarmed=True)
                completed = (
                    outcome.decision == "completed" and outcome.disarm_acknowledged
                )
            finally:
                self._active_motion = None
                if not completed:
                    self._hold_motion()
        if motion.cancel_called or outcome is None:
            return EdgeReply(result="unavailable", state="motion_interrupted")
        return EdgeReply(
            result="ok" if completed else "refused", state=outcome.reason, robot=outcome
        )
