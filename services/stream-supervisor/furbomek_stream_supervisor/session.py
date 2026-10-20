"""The private media-session state machine."""

from __future__ import annotations

from collections.abc import Mapping
from threading import Event

import anyio

from .health import publish as publish_health
from .models import (
    Freshness,
    FreshnessHealth,
    HealthState,
    RuntimePaths,
    RuntimeSettings,
    WorkerStatus,
)
from .ownership import record_owners
from .processes import ManagedProcess, cleanup_processes
from .readiness import ReadinessResult
from .shutdown import shutdown_session
from .support import (
    BACKOFF_S,
    MAX_RESTARTS,
    POLL_S,
    RESTART_WINDOW_S,
    Dependencies,
    SessionError,
    WorkerState,
)


class Session:
    """Own startup, readiness, restart, health, and whole-session cleanup."""

    settings: RuntimeSettings
    paths: RuntimePaths
    env: Mapping[str, str]
    deps: Dependencies
    states: dict[str, WorkerState]
    children: dict[str, ManagedProcess]
    freshness: FreshnessHealth
    state: HealthState
    stop_reason: str | None
    stop_requested: bool
    success: bool
    started_at_ns: int
    configure_stop: Event
    startup_deadline: float | None

    def __init__(
        self,
        settings: RuntimeSettings,
        paths: RuntimePaths,
        env: Mapping[str, str],
        deps: Dependencies,
    ) -> None:
        self.settings = settings
        self.paths = paths
        self.env = dict(env)
        self.deps = deps
        self.states = {worker.key: WorkerState(worker) for worker in deps.workers(settings, paths)}
        self.children = {}
        empty = Freshness(age_s=None, fresh=False, schema_valid=False)
        self.freshness = FreshnessHealth(tracking=empty, activity=empty)
        self.state = HealthState.STARTING
        self.stop_reason = None
        self.stop_requested = False
        self.success = False
        self.started_at_ns = int(deps.clock.time() * 1_000_000_000)
        self.configure_stop = Event()
        self.startup_deadline = None

    def request_stop(self, reason: str, *, success: bool) -> None:
        """Request a bounded whole-session stop."""
        self.stop_requested = True
        self.stop_reason = reason
        self.success = success
        self.configure_stop.set()

    def publish(self) -> None:
        """Atomically publish one validated health document."""
        publish_health(self)

    def _spawn(self, state: WorkerState) -> None:
        record_owners(self.paths.owners, self.children, pending_spawn=True)
        state.child = self.deps.spawn(state.definition, self.env, self.paths.media_root / "logs")
        self.children[state.definition.key] = state.child
        record_owners(self.paths.owners, self.children)
        state.status = WorkerStatus.STARTING
        state.restart_at = None

    def _alive(self, *, initial: bool) -> bool:
        return all(
            state.child is not None and state.child.poll() is None
            for state in self.states.values()
            if not initial or not state.definition.starts_after_configure
        )

    def _producer_generation_current(self) -> bool:
        """Require both producer files to be published after this session began."""
        try:
            return all(
                (self.paths.kinect_dir / name).stat().st_mtime_ns >= self.started_at_ns
                for name in ("tracking.json", "activity.json")
            )
        except OSError:
            return False

    async def _wait_ready(self, *, initial: bool = True) -> None:
        deadline = self.startup_deadline or (
            self.deps.clock.monotonic() + self.settings.readiness_timeout_s
        )
        self.startup_deadline = deadline
        while self.deps.clock.monotonic() < deadline:
            if self.stop_requested:
                raise SessionError("interrupted")
            await self._observe_workers()
            if self.stop_requested:
                raise SessionError(self.stop_reason or "interrupted")
            if any(state.status is WorkerStatus.FAILED for state in self.states.values()):
                raise SessionError("worker restart limit exceeded during readiness")
            alive = self._alive(initial=initial)
            result = self.deps.readiness(self.paths.kinect_dir, self.deps.clock.time, alive)
            self.freshness = result.freshness
            self.publish()
            if result.ready and self._producer_generation_current():
                return
            await self.deps.sleep(min(POLL_S, max(0.001, deadline - self.deps.clock.monotonic())))
        msg = "media readiness timed out"
        raise SessionError(msg)

    async def _reap_exit(self, key: str, code: int) -> None:
        state = self.states[key]
        child = state.child
        if child is None:
            return
        cleaned = await cleanup_processes(
            {key: child}, self.deps.clock, self.deps.sleep, grace_s=0.25
        )
        if not cleaned:
            state.status = WorkerStatus.FAILED
            raise SessionError(f"{key} cleanup did not complete; refusing another owner")
        _ = self.children.pop(key, None)
        state.child = None
        record_owners(self.paths.owners, self.children)
        state.last_exit = f"exit {code}"

    def schedule_restart(self, state: WorkerState) -> None:
        now = self.deps.clock.monotonic()
        while state.restart_times and now - state.restart_times[0] >= RESTART_WINDOW_S:
            _ = state.restart_times.popleft()
        if len(state.restart_times) >= MAX_RESTARTS:
            state.status = WorkerStatus.FAILED
            msg = f"{state.definition.key} restart limit exceeded"
            raise SessionError(msg)
        state.restart_times.append(now)
        state.restart_at = now + BACKOFF_S[len(state.restart_times) - 1]
        state.status = WorkerStatus.BACKOFF

    async def _observe_workers(self) -> None:
        now = self.deps.clock.monotonic()
        for state in self.states.values():
            if state.child is None:
                if (
                    state.restart_at is not None
                    and now >= state.restart_at
                    and not self.stop_requested
                ):
                    self._spawn(state)
                continue
            code = state.child.poll()
            if code is None:
                if state.status is WorkerStatus.STARTING:
                    state.status = WorkerStatus.RUNNING
                continue
            await self._reap_exit(state.definition.key, code)
            if state.definition.presentation and code == 0:
                self.request_stop(f"{state.definition.key} closed by operator", success=True)
                return
            self.schedule_restart(state)

    async def _start(self) -> None:
        for state in self.states.values():
            if not state.definition.starts_after_configure:
                self._spawn(state)
        await self._wait_ready()
        if self.stop_requested:
            raise SessionError("interrupted")
        configure = self.deps.configure_with_stop
        if configure is None:
            configured = await anyio.to_thread.run_sync(
                self.deps.configure,
                self.paths,
                self.env,
                self.settings.readiness_timeout_s,
                abandon_on_cancel=True,
            )
        else:
            configured = await anyio.to_thread.run_sync(
                configure,
                self.paths,
                self.env,
                max(0.0, (self.startup_deadline or 0.0) - self.deps.clock.monotonic()),
                self.configure_stop,
                abandon_on_cancel=True,
            )
        if not configured:
            msg = "OBS configuration failed"
            raise SessionError(msg)
        if self.stop_requested:
            raise SessionError("interrupted")
        for state in self.states.values():
            if state.definition.starts_after_configure:
                self._spawn(state)
        await self.deps.sleep(0)
        await self._wait_ready(initial=False)
        self.state = HealthState.READY
        self.publish()

    async def _loop(self) -> None:
        while not self.stop_requested:
            await self._observe_workers()
            result: ReadinessResult = self.deps.readiness(
                self.paths.kinect_dir, self.deps.clock.time, self._alive(initial=False)
            )
            result_ready = result.ready and self._producer_generation_current()
            self.freshness = result.freshness
            if self.state is HealthState.READY and not result_ready:
                self.state = HealthState.DEGRADED
            elif (
                self.state is HealthState.DEGRADED
                and result_ready
                and all(state.status is WorkerStatus.RUNNING for state in self.states.values())
            ):
                self.state = HealthState.READY
            self.publish()
            await self.deps.sleep(POLL_S)

    async def run(self) -> int:
        """Run one complete private session."""
        self.publish()
        try:
            await self._start()
            await self._loop()
        except SessionError as error:
            self.stop_reason = error.reason
            self.state = HealthState.FAILED
        except OSError as error:
            self.stop_reason = f"session I/O failed: {error}"
            self.state = HealthState.FAILED
        finally:
            await shutdown_session(self)
        return 0 if self.success else 1
