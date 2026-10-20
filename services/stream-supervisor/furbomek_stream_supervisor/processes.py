"""Process-group ownership and bounded shutdown."""

from __future__ import annotations

import os
import signal
import subprocess
from collections.abc import Awaitable, Callable, Mapping
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Protocol

from .models import WorkerDefinition


class Clock(Protocol):
    """Monotonic clock used by lifecycle tests and production."""

    def monotonic(self) -> float:
        """Return monotonic seconds."""
        ...


Sleep = Callable[[float], Awaitable[None]]


@dataclass(slots=True)
class ManagedProcess:
    """A child process and its private process group."""

    process: subprocess.Popen[bytes]
    log_handle: BinaryIO
    log_path: Path
    pgid: int

    @property
    def pid(self) -> int:
        """Return the direct child PID."""
        return self.process.pid

    def poll(self) -> int | None:
        """Return the child exit code without blocking."""
        return self.process.poll()

    def close(self) -> None:
        """Close the supervisor-owned log descriptor."""
        self.log_handle.close()


def spawn_process(
    definition: WorkerDefinition,
    env: Mapping[str, str],
    log_dir: Path,
) -> ManagedProcess:
    """Start one child in a fresh process group with redirected output."""
    log_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    log_path = log_dir / definition.log_name
    handle = log_path.open("ab")
    try:
        process = subprocess.Popen(
            definition.argv,
            stdin=subprocess.DEVNULL,
            stdout=handle,
            stderr=subprocess.STDOUT,
            env=dict(env),
            start_new_session=True,
        )
    except OSError:
        handle.close()
        raise
    return ManagedProcess(process=process, log_handle=handle, log_path=log_path, pgid=process.pid)


def group_alive(pgid: int) -> bool:
    """Return whether a process group still exists."""
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def signal_group(child: ManagedProcess, value: signal.Signals) -> None:
    """Send a signal to every process in a child-owned group."""
    try:
        os.killpg(child.pgid, value)
    except ProcessLookupError:
        return


async def cleanup_processes(
    children: Mapping[str, ManagedProcess],
    clock: Clock,
    sleep: Sleep,
    grace_s: float = 5.0,
) -> bool:
    """Terminate, escalate, reap, and close all child process groups."""

    def reap_exited() -> None:
        for child in children.values():
            if child.poll() is not None:
                with suppress(subprocess.TimeoutExpired, ChildProcessError):
                    _ = child.process.wait(timeout=0)

    for child in children.values():
        signal_group(child, signal.SIGTERM)
    deadline = clock.monotonic() + grace_s
    while clock.monotonic() < deadline and any(group_alive(c.pgid) for c in children.values()):
        reap_exited()
        await sleep(min(0.05, max(0.001, deadline - clock.monotonic())))
    all_reaped = True
    for child in children.values():
        if group_alive(child.pgid):
            signal_group(child, signal.SIGKILL)
    for child in children.values():
        try:
            remaining = max(0.0, deadline - clock.monotonic())
            _ = child.process.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            all_reaped = False
        finally:
            child.close()
    return all_reaped and all(
        child.poll() is not None and not group_alive(child.pgid) for child in children.values()
    )
