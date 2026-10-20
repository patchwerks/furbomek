from __future__ import annotations

import json
import sys
import time
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from furbomek_stream_supervisor.models import (
        BotDesktopRuntime,
        RuntimePaths,
        RuntimeSettings,
        WorkerDefinition,
    )


def command(code: str) -> tuple[str, ...]:
    return (sys.executable, "-c", code)


def producer_command(directory: Path, ending: str = "time.sleep(30)") -> tuple[str, ...]:
    return command(
        f"""import json, time
from datetime import datetime, timezone
from pathlib import Path
d=Path({str(directory)!r}); now=int(time.time()*1000)
(d/'tracking.json').write_text(json.dumps({{'schema':'furbomek.vision.v1','sequence':1,'capture_monotonic_ns':1,'produced_monotonic_ns':2,'produced_unix_ms':now,'frame_file':'frame-0.bin','image_file':'frame-0.jpg.bin','optical_file':'frame-0.optical.bin','valid_points':0,'capture_fps':30.0,'ttl_ms':600}}))
(d/'activity.json').write_text(json.dumps({{'schemaVersion':'furbomek.character.v1','kind':'agent.activity','source':'hermes-adapter','audience':'public','sensitivity':'public','seq':1,'observedAt':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),'ttlMs':30000,'payload':{{'title':'Fixture','summary':'Ready','status':'IDLE','tool':'AGENT'}}}}))
{ending}"""
    )


def never_bot(paths: RuntimePaths, env: Mapping[str, str], timeout_s: float) -> BotDesktopRuntime:
    _ = paths, env, timeout_s
    raise AssertionError("screen helper must remain off")


def always_configure(paths: RuntimePaths, env: Mapping[str, str], timeout_s: float) -> bool:
    _ = paths, env, timeout_s
    return True


def fail_configure(paths: RuntimePaths, env: Mapping[str, str], timeout_s: float) -> bool:
    _ = paths, env, timeout_s
    return False


def no_workers(settings: RuntimeSettings, paths: RuntimePaths) -> tuple[WorkerDefinition, ...]:
    _ = settings, paths
    return ()


class TestClock:
    value: float = 400.0

    def monotonic(self) -> float:
        return self.value

    def time(self) -> float:
        return time.time()


def fresh_artifacts(directory: Path) -> None:
    now_ms = int(time.time() * 1000)
    _ = (directory / "tracking.json").write_text(
        json.dumps(
            {
                "schema": "furbomek.vision.v1",
                "sequence": 1,
                "capture_monotonic_ns": 1,
                "produced_monotonic_ns": 2,
                "produced_unix_ms": now_ms,
                "frame_file": "frame-0.bin",
                "image_file": "frame-0.jpg.bin",
                "optical_file": "frame-0.optical.bin",
                "valid_points": 0,
                "capture_fps": 30.0,
                "ttl_ms": 600,
            }
        ),
        encoding="utf-8",
    )
    _ = (directory / "activity.json").write_text(
        json.dumps(
            {
                "schemaVersion": "furbomek.character.v1",
                "kind": "agent.activity",
                "source": "hermes-adapter",
                "audience": "public",
                "sensitivity": "public",
                "seq": 1,
                "observedAt": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                "ttlMs": 30_000,
                "payload": {
                    "title": "Fixture",
                    "summary": "Ready",
                    "status": "IDLE",
                    "tool": "AGENT",
                },
            }
        ),
        encoding="utf-8",
    )
