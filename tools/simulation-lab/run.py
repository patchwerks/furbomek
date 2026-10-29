#!/usr/bin/env python3
"""Compile reviewed pure native sources and run bounded offline fixture suites."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
GUARD = ROOT / "firmware/freenove-guard"
DIAGNOSTIC = ROOT / "firmware/robot-safety"
GUARD_SOURCES = tuple(GUARD / "src" / f"{name}.cpp" for name in (
    "frame", "frame_decode", "guard", "rf_link", "manual", "dispatcher",
    "scheduler", "esp_diag", "metadata",
))
DIAGNOSTIC_SOURCES = tuple(DIAGNOSTIC / "src" / f"{name}.cpp" for name in (
    "safety_kernel", "frame", "protocol",
))
SUITES = {
    "guard-scenarios": (GUARD, GUARD_SOURCES + (Path(__file__).with_name("guard_scenarios.cpp"),)),
    "guard-regression": (GUARD, GUARD_SOURCES + (
        GUARD / "tests/test_guard.cpp", GUARD / "tests/test_stop_routes.cpp",
    )),
    "diagnostic-regression": (DIAGNOSTIC, DIAGNOSTIC_SOURCES + tuple(
        DIAGNOSTIC / "tests" / f"{name}.cpp" for name in (
            "test_main", "test_kernel", "test_frame", "test_integration",
        )
    )),
}


def inventory() -> list[dict[str, object]]:
    """Report other gates without running hooks, services, installers or tools."""
    return [
        {"component": "locked-python-media", "entrypoint": "bash tools/verify-media.sh",
         "prerequisites_found": {"uv": bool(shutil.which("uv")), "godot": bool(shutil.which("godot"))},
         "status": "not_run", "limit": "Existing locked tests, lint, types and real Godot fixtures remain required."},
        {"component": "avr-build", "entrypoint": "firmware/freenove-guard/build.sh --all; firmware/robot-safety/build.sh --all",
         "status": "not_run", "limit": "Requires reviewed extracted AVR toolchain; native tests do not qualify installed firmware."},
        {"component": "legacy-npm", "entrypoint": "npm ci; npm run build",
         "status": "not_run", "limit": "Postinstall executes builds; dependency and security baseline is separate work."},
        {"component": "speech-cancellation-and-pcm", "status": "blocked",
         "issue": "https://github.com/patchwerks/furbomek/issues/7",
         "limit": "Canonical broker, speech and consumer dependencies must be accepted; no invented audio clock or live playback."},
    ]


def source_hashes(paths: tuple[Path, ...], root: Path) -> dict[str, str]:
    # Include headers: a changed declaration must change provenance too.
    inputs = set(paths) | set((root / "include").rglob("*.h")) | set((root / "tests").glob("*.h"))
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(inputs)}


def invoke(command: list[str], env: dict[str, str], timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                          check=False, timeout=timeout)


def run_suite(name: str, compiler: str, directory: Path, env: dict[str, str]) -> dict[str, object]:
    root, sources = SUITES[name]
    target = directory / name
    result: dict[str, object] = {"suite": name, "evidence": "offline-native-fixtures",
                                "source_sha256": source_hashes(sources, root)}
    command = [compiler, "-std=c++17", "-Wall", "-Wextra", "-Wpedantic", "-Werror",
               "-Wshadow", "-Wconversion", "-I", str(root / "include"),
               *map(str, sources), "-o", str(target)]
    try:
        compiled = invoke(command, env, 60)
        if compiled.returncode:
            return {**result, "status": "failed", "stage": "compile",
                    "output": (compiled.stdout + compiled.stderr)[-12000:]}
        executed = invoke([str(target)], env, 30)
        return {**result, "status": "passed" if executed.returncode == 0 else "failed",
                "stage": "execute", "exit_code": executed.returncode,
                "output": (executed.stdout + executed.stderr)[-12000:]}
    except subprocess.TimeoutExpired:
        return {**result, "status": "failed", "stage": "timeout"}
    except OSError as error:
        return {**result, "status": "blocked", "stage": "process", "error": type(error).__name__}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", action="store_true", help="List scope and deferred gates; execute nothing")
    parser.add_argument("--suite", choices=tuple(SUITES), action="append", help="Select a suite; default runs all three")
    parser.add_argument("--cxx", default="c++", help="Compiler executable path/name, never a shell command")
    args = parser.parse_args()
    report: dict[str, object] = {
        "schema": "furbomek.simulation-lab.v1", "scope": "offline-native-fixtures",
        "live_robot_access": False, "other_gates": inventory(),
        "qualification": "No physical motion, electrical timing, real network, audio, HIL or deployment acceptance.",
    }
    if args.inventory:
        report["suites"] = list(SUITES)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    compiler = shutil.which(args.cxx)
    if compiler is None:
        print(json.dumps({**report, "status": "blocked", "reason": "C++ compiler unavailable"}, indent=2))
        return 2
    with tempfile.TemporaryDirectory(prefix="furbomek-simulation-") as temporary:
        directory = Path(temporary)
        home = directory / "home"
        home.mkdir()
        # Environment hygiene is not OS isolation; use a credential-free worker.
        env = {"PATH": os.defpath, "HOME": str(home), "TMPDIR": str(directory),
               "LANG": "C", "LC_ALL": "C"}
        try:
            version = invoke([compiler, "--version"], env, 10)
            report["compiler"] = version.stdout.splitlines()[0] if version.stdout else "unknown"
        except (OSError, subprocess.TimeoutExpired):
            report["compiler"] = "unavailable"
        results = [run_suite(name, compiler, directory, env) for name in dict.fromkeys(args.suite or SUITES)]
        report["results"] = results
        report["status"] = "passed" if all(item["status"] == "passed" for item in results) else "failed"
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
