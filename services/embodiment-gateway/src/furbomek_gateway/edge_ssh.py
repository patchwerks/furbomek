"""Reverse Unix forwarding and bounded text-only HUD intake."""

import re
import shlex
from datetime import datetime
from pathlib import Path
from subprocess import DEVNULL
from typing import ClassVar, Final, Literal, final

import anyio
from anyio.streams.buffered import BufferedByteReceiveStream
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from furbomek_gateway.edge_protocol import CLOCK_SKEW_MS, MESSAGE_LIMIT, unix_ms
from furbomek_gateway.edge_robot import RobotBench

_SESSION_PATH: Final = re.compile(
    r"/(?:[A-Za-z0-9_-]+/|\.[A-Za-z0-9_-]+/)+link\.[a-z0-9_]+"
)


class LinkSettings(BaseModel):
    """Operator-selected SSH alias and fixed remote relay command."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)
    host: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9.-]+$")
    relay_command: tuple[str, ...] = Field(min_length=1)


class _HudLine(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", strict=True)
    age_s: int = Field(ge=0, le=86400)
    category: str = Field(min_length=1, max_length=12)
    action: str = Field(min_length=1, max_length=48)
    detail: str = Field(max_length=60)
    status: Literal["ok", "error", "running"]


class _HudPayload(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", strict=True)
    title: str = Field(min_length=1, max_length=180)
    summary: str = Field(max_length=180)
    status: str = Field(min_length=1, max_length=24)
    tool: str = Field(min_length=1, max_length=12)
    timeline: tuple[_HudLine, ...] = Field(max_length=6)


class _HudEvent(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", strict=True)
    schema_version: Literal["furbomek.character.v1"] = Field(alias="schemaVersion")
    kind: Literal["agent.activity"]
    source: Literal["hermes-adapter"]
    audience: Literal["public"]
    sensitivity: Literal["public"]
    seq: int = Field(ge=0)
    observed_at: str = Field(
        alias="observedAt", pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$"
    )
    ttl_ms: int = Field(alias="ttlMs", ge=1, le=5000)
    payload: _HudPayload

    def current(self) -> bool:
        observed_ms = int(datetime.fromisoformat(self.observed_at).timestamp() * 1000)
        return -CLOCK_SKEW_MS <= unix_ms() - observed_ms <= self.ttl_ms


@final
class ReverseLink:
    """Hold one reverse socket and remove HUD and bench authority on disconnect."""

    def __init__(
        self, settings: LinkSettings, socket_path: Path, activity: Path
    ) -> None:
        """Record the private socket and the text publication destination."""
        self._settings = settings
        self._socket_path = socket_path
        self._activity = activity
        self._seq = -1

    def _ssh(self) -> tuple[str, ...]:
        return (
            "/usr/bin/ssh",
            "-T",
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=8",
            "-o",
            "StrictHostKeyChecking=yes",
            "-o",
            "UpdateHostKeys=no",
            "-o",
            "ExitOnForwardFailure=yes",
            "-o",
            "ServerAliveInterval=8",
            "-o",
            "ServerAliveCountMax=2",
            "-o",
            "ControlMaster=no",
            "-o",
            "ControlPath=none",
            "-o",
            "ForwardAgent=no",
            "-o",
            "ForwardX11=no",
        )

    async def _session(self) -> str | None:
        command = shlex.join((*self._settings.relay_command, "create"))
        with anyio.fail_after(15):
            result = await anyio.run_process(
                (
                    *self._ssh(),
                    "-o",
                    "ClearAllForwardings=yes",
                    self._settings.host,
                    command,
                ),
                check=False,
                stderr=DEVNULL,
            )
        if result.returncode:
            return None
        candidate = result.stdout.decode("ascii").strip()
        return candidate if _SESSION_PATH.fullmatch(candidate) else None

    def _accept(self, data: bytes) -> None:
        event = _HudEvent.model_validate_json(data)
        if event.seq <= self._seq or not event.current():
            return
        pending = self._activity.with_name("activity.next.json")
        _ = pending.write_bytes(data)
        _ = pending.replace(self._activity)
        self._seq = event.seq

    async def _run_link(self, bench: RobotBench) -> None:
        session = await self._session()
        if session is None:
            return
        forward = f"{session}/control.sock:{self._socket_path}"
        command = shlex.join((*self._settings.relay_command, "attach", session))
        argv = (*self._ssh(), "-R", forward, self._settings.host, command)
        async with await anyio.open_process(argv, stderr=None) as child:
            try:
                if child.stdout is None:
                    return
                stream = BufferedByteReceiveStream(child.stdout)
                with anyio.fail_after(20):
                    if await stream.receive_until(b"\n", MESSAGE_LIMIT) != b"READY":
                        return
                await bench.tunnel_changed(connected=True)
                while True:
                    with anyio.fail_after(6):
                        payload = await stream.receive_until(b"\n", MESSAGE_LIMIT)
                    self._accept(payload)
            finally:
                if child.returncode is None:
                    child.terminate()

    async def run(self, bench: RobotBench) -> None:
        """Recreate a fresh SSH session after a disconnect."""
        while True:
            try:
                await self._run_link(bench)
            except (
                OSError,
                UnicodeError,
                ValueError,
                TimeoutError,
                ValidationError,
                anyio.EndOfStream,
                anyio.IncompleteRead,
                anyio.DelimiterNotFound,
            ):
                pass
            finally:
                with anyio.CancelScope(shield=True):
                    await bench.tunnel_changed(connected=False)
                    self._activity.unlink(missing_ok=True)
            await anyio.sleep(2)
