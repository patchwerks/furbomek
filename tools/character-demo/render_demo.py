#!/usr/bin/env python3
"""Exercise the real broker and rendered Control with synthetic local input only.

Run in an isolated worker with the locked hermes-activity environment. This
does not start the camera viewer scene, OBS, Hermes, audio or hardware services.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/hermes-activity"))
from runtime import ActivityBroker, RunConfig  # noqa: E402


def run(godot: Path, output: Path, *, full_canvas: bool = False) -> None:
    output.mkdir(mode=0o700)
    private = output / "private"
    private.mkdir(mode=0o700)
    captures = output / "captures"
    captures.mkdir(mode=0o700)
    spool = private / "input.jsonl"
    spool.touch(mode=0o600)
    public = output / "public"
    broker = ActivityBroker(
        RunConfig(
            spool,
            private / "profile",
            public,
            character_session="offline-render-fixture",
        )
    )
    log = (output / "godot.log").open("w")
    process = subprocess.Popen(
        [
            str(godot),
            "--windowed",
            "--resolution",
            "1280x720",
            "--path",
            str(ROOT / "tools/kinect2/godot"),
            "--rendering-method",
            "gl_compatibility",
            "--audio-driver",
            "Dummy",
            "--script",
            "res://character_render_runner.gd",
            "--",
            str(public),
            str(captures),
            "full" if full_canvas else "focus",
        ],
        stdout=log,
        stderr=subprocess.STDOUT,
    )
    try:
        deadline = time.monotonic() + 20
        while not (captures / "ready").exists():
            if process.poll() is not None or time.monotonic() > deadline:
                raise RuntimeError("Renderer did not become ready; inspect godot.log")
            time.sleep(0.025)
        # Arrival offsets deliberately differ from the broker's 120ms poll period.
        cases = [
            (0.07, "idle", None),
            (3.02, "thinking", None),
            (6.11, "speaking", "fixture-a"),
            (9.04, "interrupted", "fixture-a"),
            (12.09, "speaking", "fixture-a"),
            (15.03, "error", None),
        ]
        started = time.monotonic()
        next_poll = started
        index = 0
        events = []
        while time.monotonic() - started < 19:
            if process.poll() is not None:
                raise RuntimeError("Renderer exited before demonstration completed")
            elapsed = time.monotonic() - started
            if index < len(cases) and elapsed >= cases[index][0]:
                _, phase, identity = cases[index]
                observed = time.time_ns() // 1_000_000
                event = {
                    "schema_version": "furbomek.character-input.v1",
                    "session": "offline-render-fixture",
                    "seq": index,
                    "observed_ms": observed,
                    "ttl_ms": 30000,
                    "phase": phase,
                }
                if identity:
                    event["cancel_of" if phase == "interrupted" else "utterance"] = (
                        identity
                    )
                wrapper = {
                    "v": 1,
                    "kind": "character",
                    "ts_ms": observed,
                    "session": "offline-render-fixture",
                    "action": "fixture",
                    "detail": "",
                    "character": event,
                }
                with spool.open("a") as stream:
                    stream.write(json.dumps(wrapper) + "\n")
                events.append(
                    {
                        "case": index,
                        "requested": phase.upper(),
                        "expected": "INTERRUPTED" if index == 4 else phase.upper(),
                        "produced_ms": observed,
                        "replay_rejected": index == 4,
                    }
                )
                index += 1
            if time.monotonic() >= next_poll:
                broker.step(time.time_ns() // 1_000_000)
                next_poll += 0.12
            time.sleep(0.005)
        (captures / "finish").touch()
        if process.wait(timeout=10) != 0:
            raise RuntimeError("Renderer failed")
        (output / "events.json").write_text(json.dumps(events, indent=2) + "\n")
        print(f"Rendered fixture complete: {len(events)} inputs")
    finally:
        broker.reader.close()
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=10)
        log.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--godot", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--full-canvas",
        action="store_true",
        help="Show the native broadcast layout instead of the readable status preview",
    )
    args = parser.parse_args()
    if not args.godot.is_absolute() or not args.godot.is_file():
        parser.error("--godot must be an existing absolute executable path")
    run(args.godot, args.output.resolve(), full_canvas=args.full_canvas)
