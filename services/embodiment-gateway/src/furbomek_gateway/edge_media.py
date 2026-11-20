"""Private macOS capture workers and the local OBS frontend channel."""

import os
import time
from pathlib import Path
from subprocess import DEVNULL, STDOUT
from typing import TYPE_CHECKING, ClassVar, Final, final
from uuid import uuid4

import anyio
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from furbomek_gateway.edge_protocol import (
    EdgeReply,
    KinectCommand,
    KinectHealth,
    ObsCommand,
    ObsHealth,
    unix_ms,
)

if TYPE_CHECKING:
    from anyio.abc import Process

OBS_PROFILE: Final = "Furbomek Mac Test"
_LOCAL_OBS: Final = "/Applications/OBS.app"
_SERIAL_TTL: Final = 4


class MediaSettings(BaseModel):
    """Only locally installed paths can select binaries and media assets."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)
    runtime: Path
    repository: Path
    media_root: Path
    capture: Path
    tracker_python: Path
    godot: Path


class _Track(BaseModel):
    id: str


class _Tracking(BaseModel):
    sequence: int
    capture_fps: float
    produced_unix_ms: int
    ttl_ms: int = Field(gt=0, le=600)
    tracks: tuple[_Track, ...]


class _ObsRequest(BaseModel):
    request_id: str
    command: ObsCommand
    expires_at: int


def _replace_private(path: Path, data: str) -> None:
    stage = path.with_name(path.name + ".next")
    _ = stage.write_text(data, encoding="utf-8")
    _ = stage.replace(path)


@final
class MacMedia:
    """Own the three foreground workers and one serialized OBS mailbox."""

    def __init__(self, settings: MediaSettings) -> None:
        """Initialize a stopped session in the private runtime directory."""
        self.settings = settings
        self.frames = settings.runtime / "frames"
        self.frames.mkdir(mode=0o700, exist_ok=True)
        self._workers: list[Process] = []
        self._camera_lock = anyio.Lock()
        self._obs_lock = anyio.Lock()

    def health(self) -> KinectHealth:
        """Require the owned worker set and a fresh tracker publication."""
        running = bool(self._workers) and all(
            p.returncode is None for p in self._workers
        )
        if not running:
            return KinectHealth(running=False, fresh=False)
        try:
            track_file = self.frames / "tracking.json"
            with track_file.open("rb") as file:
                track = _Tracking.model_validate_json(file.read(65536))
            if 0 <= unix_ms() - track.produced_unix_ms <= track.ttl_ms:
                return KinectHealth(
                    running=True,
                    fresh=True,
                    sequence=track.sequence,
                    capture_fps=track.capture_fps,
                    object_locked=any(
                        item.id == "object-furbomek" for item in track.tracks
                    ),
                )
        except (OSError, ValidationError):
            return KinectHealth(running=True, fresh=False)
        return KinectHealth(running=True, fresh=False)

    async def _start(self) -> None:
        repo = self.settings.repository
        commands = (
            ("capture", (str(self.settings.capture),)),
            (
                "tracker",
                (
                    str(self.settings.tracker_python),
                    str(repo / "services/camera-capture/track.py"),
                ),
            ),
            (
                "godot",
                (
                    str(self.settings.godot),
                    "--path",
                    str(repo / "tools/kinect2/godot"),
                    "--windowed",
                    "--position",
                    "32,65",
                    "--max-fps",
                    "30",
                ),
            ),
        )
        env = dict(os.environ)
        env.update(
            FURBOMEK_KINECT_DIR=str(self.frames),
            FURBOMEK_MEDIA_ROOT=str(self.settings.media_root),
            MPLCONFIGDIR=str(self.settings.runtime / "matplotlib-cache"),
        )
        for name, command in commands:
            with (self.settings.runtime / f"{name}.log").open("ab") as log:
                self._workers.append(
                    await anyio.open_process(
                        command, stdin=DEVNULL, stdout=log, stderr=STDOUT, env=env
                    )
                )

    async def _stop(self) -> None:
        with anyio.CancelScope(shield=True):
            for child in self._workers:
                if child.returncode is None:
                    child.terminate()
            with anyio.move_on_after(7):
                for child in self._workers:
                    _ = await child.wait()
            for child in self._workers:
                if child.returncode is None:
                    child.kill()
            for child in self._workers:
                await child.aclose()
            self._workers.clear()
            (self.frames / "tracking.json").unlink(missing_ok=True)
            (self.frames / "view.json").unlink(missing_ok=True)

    async def check_workers(self) -> None:
        """Clear a failed session rather than leaving a camera or stale renderer."""
        async with self._camera_lock:
            if self._workers and any(
                child.returncode is not None for child in self._workers
            ):
                await self._stop()

    async def close(self) -> None:
        """Stop only the capture workers owned by this process."""
        async with self._camera_lock:
            await self._stop()

    async def _start_capture(self) -> EdgeReply:
        health = self.health()
        if health.running:
            return EdgeReply(
                result="ok" if health.fresh else "starting",
                state="kinect_status",
                kinect=health,
            )
        await self._stop()
        launched = False
        try:
            await self._start()
            launched = True
        except OSError:
            return EdgeReply(result="unavailable", state="kinect_worker_start_failed")
        finally:
            if not launched:
                await self._stop()
        return EdgeReply(
            result="starting",
            state="wait_for_fresh_kinect_status",
            kinect=self.health(),
        )

    async def camera(self, command: KinectCommand) -> EdgeReply:
        """Control the named native session and approved rendering modes."""
        async with self._camera_lock:
            match command:
                case "status":
                    return EdgeReply(
                        result="ok", state="kinect_status", kinect=self.health()
                    )
                case "start":
                    return await self._start_capture()
                case "stop":
                    await self._stop()
                    return EdgeReply(
                        result="ok", state="kinect_stopped", kinect=self.health()
                    )
                case "rgb" | "crimson" | "xyz":
                    if not self.health().running:
                        return EdgeReply(result="refused", state="kinect_not_running")
                    view = (
                        '{"view":"' + command + '","issued_ms":' + str(unix_ms()) + "}"
                    )
                    _replace_private(self.frames / "view.json", view)
                    return EdgeReply(result="ok", state="godot_view_requested")

    async def obs(self, command: ObsCommand) -> EdgeReply:
        """Allow only the dedicated local frontend script to execute OBS actions."""
        async with self._obs_lock:
            if command == "open":
                argv = (
                    "/usr/bin/open",
                    "-g",
                    "-a",
                    _LOCAL_OBS,
                    "--args",
                    "--profile",
                    OBS_PROFILE,
                    "--collection",
                    OBS_PROFILE,
                    "--disable-missing-files-check",
                )
                process = await anyio.run_process(argv, check=False)
                if process.returncode:
                    return EdgeReply(result="unavailable", state="obs_launch_failed")
                return EdgeReply(result="starting", state="wait_for_obs_status")
            if (
                command in ("start_recording", "start_test_stream")
                and not self.health().fresh
            ):
                return EdgeReply(
                    result="refused", state="fresh_kinect_program_required"
                )
            return await self._obs_command(command)

    async def _obs_command(self, command: ObsCommand) -> EdgeReply:
        request = _ObsRequest(
            request_id=uuid4().hex,
            command=command,
            expires_at=int(time.time()) + _SERIAL_TTL,
        )
        destination = self.settings.runtime / "obs-request.json"
        status_file = self.settings.runtime / "obs-response.json"
        _replace_private(destination, request.model_dump_json())
        try:
            with anyio.move_on_after(6):
                while True:
                    try:
                        with status_file.open("rb") as status:
                            result = ObsHealth.model_validate_json(status.read(8192))
                        if result.request_id == request.request_id:
                            state = (
                                "obs_stop_requested"
                                if command == "stop_streaming" and result.result == "ok"
                                else "obs_frontend"
                            )
                            return EdgeReply(
                                result=result.result, state=state, obs=result
                            )
                    except (OSError, ValidationError):
                        pass
                    await anyio.sleep(0.1)
        finally:
            destination.unlink(missing_ok=True)
        return EdgeReply(result="unavailable", state="obs_frontend_no_confirmed_reply")
