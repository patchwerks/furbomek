"""Candidate evidence and I/O authority boundary regressions."""

import copy
import json
import os
import subprocess
import sys
from pathlib import Path

from cli_case import ROOT, CliCase


class BoundaryTests(CliCase):
    def test_self_attested_complete_candidate_cannot_grant_release(self):
        code, report = self.invoke("release-check", self.candidate())
        self.assertEqual(report["candidate_evidence"]["holds"], [])
        self.assertEqual(
            (
                code,
                report["status"],
                report["physical_authorization"],
                report["operational_io"],
            ),
            (2, "HOLD", False, False),
        )
        self.assertIn(
            "trusted_installed_authenticated_link_unavailable", report["holds"]
        )

    def test_release_rejects_missing_scope_digest_stale_and_previous_session(self):
        cases = (
            ("stage", "missing_evidence:stage"),
            ("auth", "missing_evidence:authenticated_link"),
            ("live", "missing_evidence:matched_live_scope"),
            ("digest", "wrong_digest:authenticated_link"),
            ("previous", "scope_mismatch:authenticated_link"),
            ("profile", "scope_mismatch:authenticated_link"),
            ("image", "scope_mismatch:authenticated_link"),
            ("expired", "stale_or_future_evidence:authenticated_link"),
        )
        for mutation, reason in cases:
            with self.subTest(mutation=mutation):
                data = self.candidate()
                if mutation in ("stage", "auth", "live"):
                    kind = {
                        "stage": "stage",
                        "auth": "authenticated_link",
                        "live": "matched_live_scope",
                    }[mutation]
                    data["evidence"] = [
                        item for item in data["evidence"] if item["kind"] != kind
                    ]
                elif mutation == "digest":
                    data["evidence"][0]["payload_sha256"] = "a" * 64
                elif mutation == "previous":
                    data["evidence"][0]["scope"]["session"] = "previous-session"
                elif mutation == "profile":
                    data["evidence"][0]["scope"]["profile_sha256"] = "a" * 64
                elif mutation == "image":
                    data["evidence"][0]["scope"]["robot_image_sha256"] = "a" * 64
                else:
                    data["evidence"][0]["expires_unix_ms"] = 0
                code, report = self.invoke("release-check", data)
                self.assertEqual(code, 2)
                self.assertIn(reason, report["holds"])

    def test_live_never_opens_supplied_operational_path(self):
        fifo = Path(self.directory.name) / "operational-pipe"
        os.mkfifo(fifo)
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "run.py"),
                "--suite",
                "approved-live",
                "--manifest",
                str(fifo),
            ],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
        report = json.loads(result.stdout)
        self.assertEqual(
            (result.returncode, report["manifest_read"], report["operational_io"]),
            (2, False, False),
        )

    def test_replay_refuses_fifo_symlink_and_duplicate_keys(self):
        for kind in ("fifo", "symlink", "duplicate"):
            with self.subTest(kind=kind):
                path = Path(self.directory.name) / kind
                if kind == "fifo":
                    os.mkfifo(path)
                elif kind == "symlink":
                    path.symlink_to(ROOT / "fixtures/representative.json")
                else:
                    path.write_text('{"schema_version":1,"schema_version":1}')
                result = subprocess.run(
                    [
                        sys.executable,
                        str(ROOT / "run.py"),
                        "--suite",
                        "replay",
                        "--manifest",
                        str(path),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=3,
                    check=False,
                )
                self.assertEqual(result.returncode, 2)
                self.assertEqual(json.loads(result.stdout)["status"], "HOLD")

    def test_unknown_pass_flags_and_coerced_types_are_rejected(self):
        for mutation in ("pass", "boolean", "float", "nan"):
            with self.subTest(mutation=mutation):
                data = copy.deepcopy(self.data)
                if mutation == "pass":
                    data["release_pass"] = True
                elif mutation == "boolean":
                    data["timings"]["frames"][0]["rendered"] = True
                elif mutation == "float":
                    data["timings"]["frames"][0]["rendered"] = 1.5
                else:
                    data["timings"]["frames"][0]["rendered"] = float("nan")
                code, report = self.invoke(data=data)
                self.assertEqual((code, report["status"]), (2, "HOLD"))

    def test_release_without_manifest_holds(self):
        code, report = self.invoke("release-check")
        self.assertEqual(
            (code, report["manifest_read"], report["holds"]),
            (2, False, ["manifest_required"]),
        )

    def test_oversized_integer_is_named_invalid_json(self):
        path = Path(self.directory.name) / "integer.json"
        path.write_text('{"schema_version":' + "1" * 5000 + "}")
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "run.py"),
                "--suite",
                "replay",
                "--manifest",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
        self.assertEqual(
            (result.returncode, json.loads(result.stdout)["holds"]),
            (2, ["invalid_json"]),
        )

    def test_release_check_rejects_special_file_before_open(self):
        fifo = Path(self.directory.name) / "forbidden-open"
        os.mkfifo(fifo)
        harness = """
import runpy, sys
from pathlib import Path
runner, forbidden = sys.argv[1:]
sys.path.insert(0, str(Path(runner).parent))
def audit(event, args):
    if event == "open" and args[0] == forbidden:
        raise RuntimeError("attempted operational open")
sys.addaudithook(audit)
sys.argv = [runner, "--suite", "release-check", "--manifest", forbidden]
runpy.run_path(runner, run_name="__main__")
"""
        result = subprocess.run(
            [sys.executable, "-c", harness, str(ROOT / "run.py"), str(fifo)],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
        self.assertEqual(result.stderr, "")
        self.assertEqual(
            (result.returncode, json.loads(result.stdout)["holds"]),
            (2, ["not_bounded_regular_file"]),
        )
