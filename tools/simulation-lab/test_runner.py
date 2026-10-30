"""Regression tests for truthful runner outcomes, not hardware behavior."""

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("simulation_lab", Path(__file__).with_name("run.py"))
assert SPEC is not None and SPEC.loader is not None
LAB = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LAB)


class RunnerTests(unittest.TestCase):
    def test_inventory_never_launches_a_process(self):
        output = io.StringIO()
        with patch("sys.argv", ["run.py", "--inventory"]), patch.object(LAB, "invoke") as launch:
            with contextlib.redirect_stdout(output):
                result = LAB.main()
        self.assertEqual(result, 0)
        launch.assert_not_called()
        self.assertEqual(json.loads(output.getvalue())["other_gates"][-1]["status"], "blocked")

    def test_missing_compiler_is_blocked_and_nonzero(self):
        output = io.StringIO()
        with patch("sys.argv", ["run.py"]), patch.object(LAB.shutil, "which", return_value=None):
            with contextlib.redirect_stdout(output):
                result = LAB.main()
        self.assertEqual(result, 2)
        self.assertEqual(json.loads(output.getvalue())["status"], "blocked")

    def test_compile_failure_does_not_execute_binary(self):
        failed = subprocess.CompletedProcess([], 1, "", "compile failure")
        with patch.object(LAB, "invoke", return_value=failed) as launch:
            result = LAB.run_suite("guard-scenarios", "/compiler", Path("/build"), {})
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["stage"], "compile")
        self.assertEqual(launch.call_count, 1)

    def test_runtime_failure_is_not_a_pass(self):
        results = [subprocess.CompletedProcess([], 0, "", ""),
                   subprocess.CompletedProcess([], 1, "", "invariant failed")]
        with patch.object(LAB, "invoke", side_effect=results):
            result = LAB.run_suite("guard-scenarios", "/compiler", Path("/build"), {})
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["exit_code"], 1)
        self.assertIn("guard_scenarios.cpp", " ".join(result["source_sha256"]))

    def test_timeout_is_not_skipped_or_passed(self):
        with patch.object(LAB, "invoke", side_effect=subprocess.TimeoutExpired("compiler", 60)):
            result = LAB.run_suite("guard-scenarios", "/compiler", Path("/build"), {})
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["stage"], "timeout")

    def test_inaccessible_process_is_blocked(self):
        with patch.object(LAB, "invoke", side_effect=PermissionError("private path")):
            result = LAB.run_suite("guard-scenarios", "/compiler", Path("/build"), {})
        self.assertEqual(result["status"], "blocked")
        self.assertNotIn("private path", str(result))


if __name__ == "__main__":
    unittest.main()
