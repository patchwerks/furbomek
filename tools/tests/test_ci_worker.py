"""Invalid bootstrap inputs must fail before invoking the container runtime."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
WORKER = ROOT / "tools/ci/worker.sh"


class WorkerInputTests(unittest.TestCase):
    def rejected(self, args, message):
        with tempfile.TemporaryDirectory() as directory:
            scratch = Path(directory)
            marker = scratch / "docker-was-called"
            docker = scratch / "docker"
            docker.write_text('#!/bin/sh\n: > "$MARKER"\nexit 99\n')
            docker.chmod(0o700)
            result = subprocess.run(
                ["/bin/bash", str(WORKER), *map(str, args)],
                env={"PATH": f"{scratch}:/usr/bin:/bin", "MARKER": str(marker)},
                capture_output=True, text=True, timeout=5,
            )
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn(message, result.stderr)
            self.assertFalse(marker.exists(), "invalid input invoked Docker")

    def test_missing_or_unknown_mode(self):
        for args in ([], ["unknown"], ["unknown", ROOT]):
            self.rejected(args, "usage:")

    def test_missing_empty_absent_or_extra_candidate(self):
        for args in (["media"], ["legacy", ""], ["media", ROOT / "does-not-exist"], ["media", ROOT, "extra"]):
            self.rejected(args, "Explicit candidate directory is required")

    def test_trusted_checkout_cannot_be_its_own_candidate(self):
        for mode in ("media", "legacy"):
            self.rejected([mode, ROOT], "Trusted helpers must be separate")

    def test_symlink_alias_of_trusted_checkout_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            alias = Path(directory) / "candidate"
            alias.symlink_to(ROOT, target_is_directory=True)
            for mode in ("media", "legacy"):
                self.rejected([mode, alias], "Trusted helpers must be separate")


class WorkerOrchestrationTests(unittest.TestCase):
    def run_fake(self, mode="legacy", version="28.0.0", failure=""):
        import json
        import os
        import sys
        with tempfile.TemporaryDirectory() as directory:
            scratch = Path(directory)
            candidate = scratch / "candidate"
            candidate.mkdir()
            (candidate / "tools").mkdir()
            (candidate / "tools/verify.sh").write_text('exit 98\n')
            log = scratch / "calls.jsonl"
            # External services are recorders. Only private temporary staging,
            # a fixed fake extraction and the real chmod touch the filesystem;
            # no candidate/container code, network or downloaded code executes.
            recorder = scratch / "recorder"
            recorder.write_text("#!" + sys.executable + '\n' + r'''
import json, os, pathlib, stat, sys, tempfile
name = pathlib.Path(sys.argv[0]).name
args = sys.argv[1:]
with open(os.environ["CALL_LOG"], "a") as stream:
    stream.write(json.dumps([name, *args]) + "\n")
if name == "mktemp":
    folder = pathlib.Path(tempfile.mkdtemp(dir=os.environ["TMPDIR"]))
    with open(os.environ["CALL_LOG"], "a") as stream:
        stream.write(json.dumps(["staging-mode", stat.S_IMODE(folder.stat().st_mode)]) + "\n")
    print(folder)
if name == "unzip":
    folder = pathlib.Path(args[args.index("-d") + 1])
    binary = folder / "Godot_v4.7.2-stable_linux.x86_64"
    binary.write_text("#!/bin/sh\nexit 97\n")
    binary.chmod(0o700)
    (folder / "private-sentinel").write_text("keep private\n")
if name == "docker":
    if args[:2] == ["run", "--rm"] and "--network" in args and args[args.index("--network") + 1] == "none":
        for arg in args:
            if arg.startswith("type=bind,source=") and arg.endswith(",target=/tools,readonly"):
                folder = pathlib.Path(arg.removeprefix("type=bind,source=").removesuffix(",target=/tools,readonly"))
                paths = [folder, folder / "Godot_v4.7.2-stable_linux.x86_64", folder / "private-sentinel"]
                with open(os.environ["CALL_LOG"], "a") as stream:
                    stream.write(json.dumps(["mounted-tool-modes", *[stat.S_IMODE(p.stat().st_mode) for p in paths]]) + "\n")
    if args[0] == "version":
        if os.environ["FAILURE"] == "version": sys.exit(1)
        print(os.environ["VERSION"])
    elif args[0] == "inspect": print("172.29.4.2")
    elif args[0] == "exec" and os.environ["FAILURE"] == "ready": sys.exit(1)
    elif args[:2] == ["run", "-d"] and "--name" in args:
        if args[args.index("--name") + 1].endswith("-scratch-keeper") and os.environ["FAILURE"] == "keeper":
            sys.exit(1)
    elif args[:2] == ["run", "--rm"] and os.environ["FAILURE"] == "worker": sys.exit(7)
''')
            recorder.chmod(0o700)
            for name in ("docker", "curl", "sha256sum", "unzip", "sleep", "mktemp"):
                (scratch / name).symlink_to(recorder)
            result = subprocess.run(
                ["/bin/bash", str(WORKER), mode, str(candidate)],
                env={"PATH": f"{scratch}:/usr/bin:/bin", "CALL_LOG": str(log),
                     "VERSION": version, "FAILURE": failure, "HOME": str(scratch),
                     "TMPDIR": str(scratch)},
                capture_output=True, text=True, timeout=10, umask=0o077)
            calls = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
            return result, calls, str(candidate)

    def test_unsupported_unknown_and_prerelease_versions_fail_before_mutation(self):
        for version, failure in (("27.5.1", ""), ("", ""), ("nonsense", ""),
                                 ("28.0.0-rc.1", ""), ("28.0.0", "version")):
            with self.subTest(version=version, failure=failure):
                result, calls, _ = self.run_fake(version=version, failure=failure)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertEqual(calls, [["docker", "version", "--format", "{{.Server.Version}}"]])

    def test_supported_versions_and_both_modes_preserve_boundaries(self):
        for mode, version in (("legacy", "28.0.0"), ("legacy", "28.5.2"), ("media", "29.0.0")):
            with self.subTest(mode=mode, version=version):
                result, calls, candidate = self.run_fake(mode, version)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(calls[0][1], "version")
                proxy_index = next(i for i, c in enumerate(calls) if c[:3] == ["docker", "run", "-d"] and "--network-alias" in c)
                launch = calls[proxy_index]
                internal = launch[launch.index("--network") + 1]
                self.assertTrue(internal.endswith("-net"))
                self.assertEqual(launch[launch.index("--network-alias") + 1], "dependency-proxy")
                self.assertIn('--bind-address "$(python -I -c "import socket; print(socket.gethostbyname(socket.gethostname()))")"', launch[-1])
                # Parse the actual launch shell with -n, never execute it.
                syntax = subprocess.run(["/bin/sh", "-n", "-c", launch[-1]], capture_output=True)
                self.assertEqual(syntax.returncode, 0, syntax.stderr)
                inspect_index = next(i for i, c in enumerate(calls) if c[:2] == ["docker", "inspect"])
                self.assertIn(internal, calls[inspect_index][3])
                ready_index = next(i for i, c in enumerate(calls) if c[:2] == ["docker", "exec"])
                self.assertEqual(calls[ready_index][-1], "172.29.4.2")
                connect_index = next(i for i, c in enumerate(calls) if c[:3] == ["docker", "network", "connect"])
                self.assertEqual(calls[connect_index][3], "bridge")
                self.assertLess(proxy_index, inspect_index)
                self.assertLess(inspect_index, ready_index)
                self.assertLess(ready_index, connect_index)
                workers = [c for c in calls if c[:3] == ["docker", "run", "--rm"]]
                self.assertTrue(workers)
                keeper_index = next(i for i, c in enumerate(calls) if c[:3] == ["docker", "run", "-d"] and "--network-alias" not in c)
                keeper = calls[keeper_index]
                keeper_name = keeper[keeper.index("--name") + 1]
                self.assertTrue(keeper_name.endswith("-scratch-keeper"))
                volume_index = next(i for i, c in enumerate(calls) if c[:3] == ["docker", "volume", "create"])
                volume = calls[volume_index][-1]
                mount = f"type=volume,source={volume},target=/scratch,volume-nocopy"
                self.assertLess(volume_index, keeper_index)
                self.assertLess(keeper_index, proxy_index)
                self.assertEqual(keeper[keeper.index("--network") + 1], "none")
                self.assertEqual(keeper[keeper.index("--cpus") + 1], "0.1")
                self.assertEqual(keeper[keeper.index("--memory") + 1], "32m")
                self.assertEqual(keeper[keeper.index("--pids-limit") + 1], "8")
                self.assertEqual([keeper[i + 1] for i, arg in enumerate(keeper) if arg == "--mount"], [mount])
                self.assertNotIn("--env", keeper)
                self.assertNotIn("--env-file", keeper)
                self.assertEqual(keeper[-3:], [
                    "python:3.12.11-bookworm@sha256:1b48a1b13ec678be8d84974541cc007d4367aaf01f985231daad1a940106efc0",
                    "sleep", "infinity",
                ])
                cleanup_index = calls.index(["docker", "rm", "-f", keeper_name])
                volume_cleanup = calls.index(["docker", "volume", "rm", "-f", volume])
                self.assertLess(cleanup_index, volume_cleanup)
                for worker in [launch, keeper, *workers]:
                    self.assertIn("--read-only", worker)
                    self.assertEqual(worker[worker.index("--cap-drop") + 1], "ALL")
                    self.assertEqual(worker[worker.index("--user") + 1], "1000:1000")
                    self.assertEqual(worker[worker.index("--security-opt") + 1], "no-new-privileges")
                    self.assertNotIn("--publish", worker)
                    self.assertNotIn("--privileged", worker)
                for worker in workers:
                    self.assertLess(keeper_index, calls.index(worker))
                    self.assertLess(calls.index(worker), cleanup_index)
                    self.assertEqual([worker[i + 1] for i, arg in enumerate(worker)
                                      if arg == "--mount" and worker[i + 1].startswith("type=volume,")], [mount])
                    self.assertEqual(worker[worker.index("--workdir") + 1], "/scratch")
                    for name in ("bootstrap-requirements.txt", "build-requirements.txt"):
                        self.assertIn(f"type=bind,source={ROOT}/tools/ci/{name},target=/trusted/{name},readonly", worker)
                    self.assertIn(f"type=bind,source={candidate},target=/source,readonly", worker)
                self.assertEqual(workers[-1][workers[-1].index("--network") + 1], "none")
                for worker in workers[:-1]:
                    self.assertEqual(worker[worker.index("--network") + 1], internal)
                if mode == "media":
                    self.assertIn(["staging-mode", 0o700], calls)
                    self.assertIn(["mounted-tool-modes", 0o755, 0o755, 0o600], calls)
                    offline = workers[-1][-1]
                    preflight = 'test -x "$FURBOMEK_GODOT"'
                    self.assertIn(preflight, offline)
                    self.assertIn("Godot is not executable by the offline worker:", offline)
                    self.assertLess(offline.index(preflight), offline.index("for service in"))
                    self.assertLess(offline.index(preflight), offline.index("bash tools/verify.sh"))
                    provision = workers[1][-1]
                    self.assertIn("pip --isolated install --proxy http://dependency-proxy:3128 --require-hashes --only-binary=:all: --no-deps -r /trusted/bootstrap-requirements.txt", provision)
                    self.assertIn("--require-hashes --no-deps --link-mode copy --target /scratch/build-inputs -r /trusted/build-requirements.txt", provision)
                    self.assertNotIn("/source/.github", provision)
                    self.assertIn("--python /usr/local/bin/python3", provision)

    def test_readiness_failure_never_attaches_egress_or_runs_candidate(self):
        result, calls, _ = self.run_fake(failure="ready")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(len([c for c in calls if c[:2] == ["docker", "exec"]]), 15)
        self.assertFalse(any(c[:3] == ["docker", "network", "connect"] for c in calls))
        self.assertFalse(any(c[:3] == ["docker", "run", "--rm"] for c in calls))
        self.assertTrue(any(c[:3] == ["docker", "rm", "-f"] for c in calls))

    def test_keeper_failure_prevents_proxy_and_candidate_execution(self):
        for mode in ("media", "legacy"):
            with self.subTest(mode=mode):
                result, calls, _ = self.run_fake(mode, failure="keeper")
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertFalse(any("--network-alias" in c for c in calls))
                self.assertFalse(any(c[:3] == ["docker", "run", "--rm"] for c in calls))
                keeper = next(c for c in calls if c[:3] == ["docker", "run", "-d"])
                name = keeper[keeper.index("--name") + 1]
                cleanup = calls.index(["docker", "rm", "-f", name])
                volume_cleanup = next(i for i, c in enumerate(calls) if c[:3] == ["docker", "volume", "rm"])
                self.assertLess(cleanup, volume_cleanup)

    def test_worker_failure_still_cleans_keeper_before_volume(self):
        for mode in ("media", "legacy"):
            with self.subTest(mode=mode):
                result, calls, _ = self.run_fake(mode, failure="worker")
                self.assertEqual(result.returncode, 7, result.stderr)
                workers = [i for i, c in enumerate(calls) if c[:3] == ["docker", "run", "--rm"]]
                self.assertEqual(len(workers), 1)
                keeper = next(c for c in calls if c[:3] == ["docker", "run", "-d"] and "--network-alias" not in c)
                name = keeper[keeper.index("--name") + 1]
                cleanup = calls.index(["docker", "rm", "-f", name])
                volume_cleanup = next(i for i, c in enumerate(calls) if c[:3] == ["docker", "volume", "rm"])
                self.assertLess(workers[0], cleanup)
                self.assertLess(cleanup, volume_cleanup)


if __name__ == "__main__":
    unittest.main()
