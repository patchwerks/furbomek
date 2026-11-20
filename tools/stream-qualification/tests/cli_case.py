"""Behavioral regression checks at the real, dependency-free CLI boundary."""

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from models import EvidenceKind


class CliCase(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.data = json.loads((ROOT / "fixtures/representative.json").read_text())

    def invoke(self, suite="replay", data=None):
        args = [sys.executable, "-s", "-E", str(ROOT / "run.py"), "--suite", suite]
        if data is not None:
            path = Path(self.directory.name) / "manifest.json"
            path.write_text(json.dumps(data))
            args += ["--manifest", str(path)]
        result = subprocess.run(
            args, capture_output=True, text=True, timeout=10, check=False
        )
        self.assertEqual(result.stderr, "")
        return result.returncode, json.loads(result.stdout)

    def candidate(self):
        data = copy.deepcopy(self.data)
        now = time.time_ns() // 1_000_000
        payload = "synthetic evidence: never installed or physically measured"
        data["evidence"] = [
            {
                "kind": kind.value,
                "scope": copy.deepcopy(data["scope"]),
                "captured_unix_ms": now - 1000,
                "expires_unix_ms": now + 60000,
                "payload": payload,
                "payload_sha256": hashlib.sha256(payload.encode()).hexdigest(),
            }
            for kind in EvidenceKind
        ]
        return data
