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


if __name__ == "__main__":
    unittest.main()
