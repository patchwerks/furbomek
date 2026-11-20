#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# How to run: python3 tools/stream-qualification/run.py --suite replay
"""Offline qualification CLI. No network, process, media or actuator adapters."""

import argparse
import hashlib
import json
import time
from dataclasses import asdict
from pathlib import Path

from faults import matrix
from metrics import evaluate
from parsing import InputError, load
from qualification import RELEASE_HOLDS, check_evidence


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--suite", required=True, choices=("replay", "approved-live", "release-check")
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        help="Explicit bounded local JSON; no referenced paths are opened",
    )
    args = parser.parse_args()
    source_files = {
        name: hashlib.sha256((Path(__file__).parent / name).read_bytes()).hexdigest()
        for name in (
            "run.py",
            "models.py",
            "parsing.py",
            "metrics.py",
            "faults.py",
            "qualification.py",
        )
    }
    report = {
        "tool_files_sha256": source_files,
        "tool_source_sha256": hashlib.sha256(
            json.dumps(source_files, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "schema_version": 1,
        "suite": args.suite,
        "release": "HOLD",
        "physical_authorization": False,
        "operational_io": False,
        "release_holds": list(RELEASE_HOLDS),
    }
    # No installed trust verifier exists in this lane. Do not even open a supplied
    # operational manifest when asked to run live, including FIFOs/device paths.
    if args.suite == "approved-live":
        report["status"] = "HOLD"
        report["manifest_read"] = False
        print(json.dumps(report, indent=2))
        return 2
    if args.suite == "release-check" and args.manifest is None:
        report.update(status="HOLD", manifest_read=False, holds=["manifest_required"])
        print(json.dumps(report, indent=2))
        return 2
    path = args.manifest or Path(__file__).parent / "fixtures" / "representative.json"
    try:
        loaded = load(path)
        data = loaded.data
        metrics = evaluate(data.timings)
        faults, fault_holds = matrix(data.faults)
        evidence = check_evidence(data, time.time_ns() // 1_000_000)
        holds = [*metrics.holds, *fault_holds]
        report.update(
            manifest_read=True,
            manifest_sha256=loaded.sha256,
            replay_model="offline_admission_policy_not_runtime_or_hil",
            scope=asdict(data.scope),
            metrics=asdict(metrics),
            faults=[asdict(item) for item in faults],
            candidate_evidence=asdict(evidence),
            replay="PASS" if not holds else "HOLD",
            holds=holds,
            evidence_scope="synthetic_or_untrusted_offline_data_only",
        )
        if args.suite == "release-check":
            report["holds"] = [*holds, *evidence.holds, *RELEASE_HOLDS]
            report["status"] = "HOLD"
            exit_code = 2
        else:
            report["status"] = report["replay"]
            exit_code = 2 if holds else 0
    except (InputError, OSError) as error:
        report.update(
            status="HOLD",
            holds=[
                error.code
                if isinstance(error, InputError)
                else "unreadable_local_manifest"
            ],
        )
        exit_code = 2
    print(json.dumps(report, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
