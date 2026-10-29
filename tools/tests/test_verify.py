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

    def run_cli(self, *args):
        return subprocess.run(
            ["/bin/bash", str(self.root / "tools/verify.sh"), *args],
            env={"PATH": str(self.root / "bin") + ":/usr/bin:/bin", "TMPDIR": str(self.root),
                 "FURBOMEK_GODOT": str(self.root / "bin/godot")},
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


if __name__ == "__main__":
    unittest.main()
