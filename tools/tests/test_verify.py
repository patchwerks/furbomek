"""Exercise the verification CLI's failure reporting in disposable checkouts."""

from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


class VerificationCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "tools").mkdir()
        shutil.copyfile(Path(__file__).parents[1] / "verify.sh", self.root / "tools/verify.sh")
        self.script("bin/rg", "exit 0\n")
        self.script("bin/uv", "exit 0\n")
        self.script("bin/godot", "exit 0\n")
        self.script("bin/g++", "exit 0\n")
        self.script("bin/sha256sum", "exit 0\n")

    def run_cli(self, *args, environment=None):
        env = {"PATH": str(self.root / "bin") + ":/usr/bin:/bin", "TMPDIR": str(self.root),
               "FURBOMEK_GODOT": str(self.root / "bin/godot")}
        for key, value in (environment or {}).items():
            if value is None:
                env.pop(key, None)
            else:
                env[key] = value
        return subprocess.run(
            ["/bin/bash", str(self.root / "tools/verify.sh"), *args],
            env=env,
            text=True, capture_output=True, check=False,
        )

    def script(self, relative, body):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("#!/bin/bash\n" + body)
        path.chmod(0o700)

    def test_help_does_not_run_checks(self):
        self.script("tools/verify-media.sh", "exit 99\n")
        result = self.run_cli("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("RUN", result.stdout)

    def test_invalid_component_runs_nothing(self):
        result = self.run_cli("media", "not-a-check")
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("RUN", result.stdout)

    def test_media_failure_is_not_a_pass(self):
        self.script("tools/verify-media.sh", "echo real-check-failed; exit 7\n")
        result = self.run_cli("media")
        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL media (exit 7)", result.stdout)
        self.assertIn("real-check-failed", result.stdout)

    def test_missing_prerequisite_is_distinct(self):
        (self.root / "bin/godot").unlink()
        result = self.run_cli("media")
        self.assertEqual(result.returncode, 2)
        self.assertIn("UNAVAILABLE media", result.stdout)

    def test_check_exit_two_is_still_a_failure(self):
        self.script("tools/verify-media.sh", "exit 2\n")
        result = self.run_cli("media")
        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL media (exit 2)", result.stdout)

    def test_later_checks_run_after_failure(self):
        self.script("tools/verify-media.sh", "exit 7\n")
        self.script("firmware/robot-safety/check-safety.sh", "exit 0\n")
        self.script("firmware/robot-safety/test.sh", "echo native-ran; exit 0\n")
        result = self.run_cli("media", "robot-native")
        self.assertEqual(result.returncode, 1)
        self.assertIn("PASS robot-native", result.stdout)
        self.assertIn("native-ran", result.stdout)

    def test_failure_inside_component_cannot_be_masked(self):
        self.script("firmware/robot-safety/check-safety.sh", "exit 9\n")
        self.script("firmware/robot-safety/test.sh", "echo must-not-run; exit 0\n")
        result = self.run_cli("robot-native")
        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL robot-native (exit 9)", result.stdout)
        self.assertNotIn("must-not-run", result.stdout)

    def vendor_environment(self):
        env = {}
        for key, relative in (
            ("FNHR_DIR", "src/FNHRBasic.cpp"),
            ("FREENOVE_ROOT", "ArduinoLibraries/FNHR.zip"),
            ("ARDUINO_CORE_DIR", "cores/arduino/Arduino.h"),
        ):
            directory = self.root / (key + " with spaces")
            path = directory / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()
            env[key] = str(directory)
        self.script("AVR with spaces/usr/bin/avr-g++", "exit 0\n")
        env["AVR_ROOT"] = str(self.root / "AVR with spaces")
        return env

    def test_each_missing_vendor_variable_blocks_guard_commands(self):
        env = self.vendor_environment()
        self.script("firmware/freenove-guard/test.sh", "echo must-not-run\n")
        self.script("firmware/freenove-guard/build.sh", "echo must-not-run\n")
        for component in ("guard-native", "guard-avr"):
            for key in ("FNHR_DIR", "FREENOVE_ROOT", "ARDUINO_CORE_DIR"):
                for absent in (None, ""):
                    with self.subTest(component=component, missing=key, value=absent):
                        result = self.run_cli(component, environment={**env, key: absent})
                        self.assertEqual(result.returncode, 2, result.stderr)
                        self.assertIn("Missing prerequisite: " + key, result.stderr)
                        self.assertIn("UNAVAILABLE " + component, result.stdout)
                        self.assertNotIn("must-not-run", result.stdout)

    def test_explicit_vendor_paths_with_spaces_run_guard_commands(self):
        env = self.vendor_environment()
        self.script("firmware/freenove-guard/test.sh", "echo guarded-native-ran\n")
        self.script("firmware/freenove-guard/build.sh", "echo guarded-avr-ran\n")
        result = self.run_cli("guard-native", "guard-avr", environment=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PASS guard-native", result.stdout)
        self.assertIn("PASS guard-avr", result.stdout)
        self.assertIn("guarded-native-ran", result.stdout)
        self.assertIn("guarded-avr-ran", result.stdout)

    def test_missing_godot_variable_blocks_media_command(self):
        self.script("tools/verify-media.sh", "echo must-not-run\n")
        for absent in (None, ""):
            with self.subTest(value=absent):
                result = self.run_cli("media", environment={"FURBOMEK_GODOT": absent})
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn("Missing prerequisite: FURBOMEK_GODOT", result.stderr)
                self.assertIn("UNAVAILABLE media", result.stdout)
                self.assertNotIn("must-not-run", result.stdout)

    def test_explicit_godot_path_with_spaces_runs_media_command(self):
        self.script("Godot with spaces/godot", "exit 0\n")
        self.script("tools/verify-media.sh", "echo explicit-media-ran\n")
        result = self.run_cli("media", environment={
            "FURBOMEK_GODOT": str(self.root / "Godot with spaces/godot"),
        })
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PASS media", result.stdout)
        self.assertIn("explicit-media-ran", result.stdout)


if __name__ == "__main__":
    unittest.main()
