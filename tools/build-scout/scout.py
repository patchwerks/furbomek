#!/usr/bin/env python3
"""Offline, advisory analysis of bounded GitHub metadata; never dispatches work."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys

SCHEMA = "xeno.build-scout.v1"
REPOSITORIES = ("patchwerks/patchwerks", "patchwerks/furbomek", "patchwerks/jabberwerk")
MAX_FILE_BYTES = 16 * 1024 * 1024
TOKEN = re.compile(r"(?:gh[pousr]_[A-Za-z0-9_]{12,}|github_pat_[A-Za-z0-9_]{12,}|sk-[A-Za-z0-9_-]{12,}|Bearer\s+\S+)", re.I)
ASSIGNMENT = re.compile(r"\b(token|password|secret|api[_-]?key)\s*[:=]\s*\S+", re.I)
STOPWORDS = frozenset("a an and are as at be by for from in into is of on or the to with".split())


def clean(value: object, limit: int = 20000) -> str:
    """Best-effort credential pattern removal, not a publication/privacy guarantee."""
    text = value if isinstance(value, str) else ""
    text = TOKEN.sub("[REDACTED]", text)
    text = ASSIGNMENT.sub(lambda m: m.group(1) + "=[REDACTED]", text)
    return "".join(c for c in text if c in "\n\t" or ord(c) >= 32)[:limit]


def canonical(repo: str, number: int | None = None, kind: str = "issues") -> str:
    if repo not in REPOSITORIES or kind not in ("issues", "pull"):
        raise ValueError("Unsupported repository or evidence kind")
    if number is not None and (type(number) is not int or number < 1):
        raise ValueError("Invalid issue number")
    return f"https://github.com/{repo}" + (f"/{kind}/{number}" if number is not None else "")


def write_private(path: Path, value: dict) -> None:
    """Exclusive creation avoids overwrites and symlink following; outputs are private."""
    data = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    if len(data.encode()) > MAX_FILE_BYTES:
        raise ValueError("Output exceeds snapshot size bound")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write(data)


def load_snapshot(path: Path) -> dict:
    with path.open("rb") as stream:
        data = stream.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES:
        raise ValueError("Snapshot exceeds size bound")
    snapshot = json.loads(data)
    validate(snapshot)
    return snapshot


def validate(snapshot: dict) -> None:
    if not isinstance(snapshot, dict) or snapshot.get("schema") != SCHEMA:
        raise ValueError("Unsupported snapshot schema")
    sources = snapshot.get("repositories")
    if not isinstance(sources, dict) or not 1 <= len(sources) <= len(REPOSITORIES):
        raise ValueError("Invalid repository collection")
    if not isinstance(snapshot.get("observed_at"), str):
        raise ValueError("Invalid observation time")
    stamp = datetime.fromisoformat(snapshot["observed_at"].replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        raise ValueError("Snapshot requires timezone")
    for repo, data in sources.items():
        canonical(repo)
        if not isinstance(data, dict) or not isinstance(data.get("coverage"), dict):
            raise ValueError("Invalid repository record")
        if any(not isinstance(v, dict) or v.get("status") not in ("complete", "partial", "unavailable") for v in data["coverage"].values()):
            raise ValueError("Invalid source coverage")
        for kind in ("issues", "pulls", "runs"):
            if not isinstance(data.get(kind), list) or len(data[kind]) > 200:
                raise ValueError("Invalid bounded item collection")
            if any(not isinstance(item, dict) for item in data[kind]):
                raise ValueError("Invalid item")
        seen = set()
        for item in data["issues"] + data["pulls"]:
            canonical(repo, item.get("number"))
            if item.get("number") is None or item["number"] in seen:
                raise ValueError("Missing or duplicate item identity")
            seen.add(item["number"])
            if item.get("state") not in ("open", "closed"):
                raise ValueError("Invalid item state")
            if not isinstance(item.get("labels"), list) or not all(isinstance(x, str) for x in item["labels"]):
                raise ValueError("Invalid labels")
            if not isinstance(item.get("assignees"), list):
                raise ValueError("Invalid assignees")
            for kind in ("comments", "blockers"):
                items = item.get(kind, [])
                if not isinstance(items, list) or len(items) > 200 or any(not isinstance(x, dict) for x in items):
                    raise ValueError("Invalid issue detail collection")


def section_blockers(body: str, repo: str) -> tuple[set[str], bool]:
    """Parse only an explicit Blocked by heading; prose remains untrusted evidence."""
    match = re.search(r"(?im)^#{1,6}\s+Blocked by\s*$([\s\S]*?)(?=^#{1,6}\s|\Z)", body)
    if not match:
        return set(), False
    section = match.group(1).strip()
    if not section or re.fullmatch(r"None[.!]?", section, re.I):
        return set(), False
    links = set(re.findall(r"https://github\.com/([\w-]+/[\w.-]+)/issues/(\d+)", section))
    urls = {f"https://github.com/{owner}/issues/{number}" for owner, number in links}
    # Qualified references first, then standalone local # references.
    qualified = re.findall(r"([\w.-]+/[\w.-]+)#(\d+)", section)
    urls.update(f"https://github.com/{owner}/issues/{number}" for owner, number in qualified)
    urls.update(canonical(repo, int(number)) for number in re.findall(r"(?<![\w/])#(\d+)", section))
    return urls, True


def analyze(snapshot: dict, *, now: datetime | None = None, max_age_hours: int = 24) -> dict:
    validate(snapshot)
    now = now or datetime.now(timezone.utc)
    observed = datetime.fromisoformat(snapshot["observed_at"].replace("Z", "+00:00"))
    age = (now - observed).total_seconds()
    stale = age < -300 or age > max_age_hours * 3600
    recommendations, duplicates, repository_summary = [], [], []
    all_items = []
    for repo, data in sorted(snapshot["repositories"].items()):
        coverage = data["coverage"]
        incomplete = sorted(key for key, value in coverage.items() if not isinstance(value, dict) or value.get("status") != "complete")
        if not all(k in coverage for k in ("metadata", "issues", "pulls", "runs")):
            incomplete.append("missing-core-source")
        failures = []
        for run in data["runs"]:
            if run.get("conclusion") in ("failure", "timed_out", "cancelled", "action_required"):
                run_id = run.get("id")
                if type(run_id) is int and run_id > 0:
                    failures.append({"url": canonical(repo) + f"/actions/runs/{run_id}", "head_sha": clean(run.get("head_sha"), 64), "conclusion": run["conclusion"]})
        repository_summary.append({"repository": repo, "evidence": canonical(repo), "incomplete_sources": incomplete,
                                   "ci_failures_observed": failures, "ci_note": "Workflow observations only; not a required-check or current-PR-head verdict."})
        for item in data["issues"] + data["pulls"]:
            kind = "pull" if item in data["pulls"] else "issues"
            url = canonical(repo, item["number"], kind)
            title = clean(item.get("title"), 512)
            all_items.append((url, title, item["state"], kind))
            if kind != "issues" or item["state"] != "open":
                continue
            labels = set(item["labels"])
            body = clean(item.get("body"))
            blockers, prose_gate = section_blockers(body, repo)
            native = item.get("blockers", [])
            for blocker in native:
                link = blocker.get("url", "")
                if re.fullmatch(r"https://github\.com/[\w.-]+/[\w.-]+/issues/[1-9]\d*", link):
                    blockers.add(link)
            # Claims never expire based on our local clock. Release needs human reconciliation.
            claim_comments = [c for c in item.get("comments", []) if re.search(r"(?im)^\s*(?:CLAIM|HANDOFF)\b", clean(c.get("body")))]
            reasons, gates = [], []
            if stale:
                gates.append("stale-or-future-snapshot")
            if item.get("body_truncated"):
                gates.append("truncated-issue-body")
            if any(c.get("body_truncated") for c in item.get("comments", [])):
                gates.append("truncated-claim-evidence")
            if incomplete:
                gates.append("incomplete-repository-coverage")
            for source in (f"issue:{item['number']}:comments", f"issue:{item['number']}:blockers"):
                if coverage.get(source, {}).get("status") != "complete":
                    gates.append("missing-claim-or-dependency-evidence")
                    break
            if "requires-hardware" in labels:
                gates.append("physical-authorization-required")
            if blockers or prose_gate or "blocked" in labels:
                gates.append("dependency-or-explicit-blocker-needs-acceptance")
            if item["assignees"] or claim_comments:
                gates.append("existing-owner-or-claim-needs-reconciliation")
            if labels.intersection({"needs-info", "ready-for-human", "needs-triage"}):
                gates.append("triage-or-human-gate")
            if "ready-for-agent" in labels:
                reasons.append("Canonical ready-for-agent label observed; not an authority grant")
            if "area:verification" in labels:
                reasons.append("Verification work can improve evidence for dependent slices")
            if not reasons:
                reasons.append("Open canonical issue; scope and acceptance need review")
            score = (20 if "ready-for-agent" in labels else 0) + (10 if "area:verification" in labels else 0)
            recommendations.append({"issue": url, "title": title, "priority_score": score,
                "disposition": "gated-review" if gates else "candidate-for-human-review", "gates": sorted(set(gates)),
                "reasons": reasons, "blocker_evidence": sorted(blockers),
                "evidence": [url] + ([url + "#issuecomment-" + str(c["id"]) for c in claim_comments if type(c.get("id")) is int])})
    for index, (left, title, state, kind) in enumerate(sorted(all_items)):
        a = set(re.findall(r"[a-z0-9]+", title.lower())) - STOPWORDS
        for right, other, other_state, other_kind in sorted(all_items)[index + 1:]:
            if state == other_state == "closed":
                continue
            b = set(re.findall(r"[a-z0-9]+", other.lower())) - STOPWORDS
            union, common = a | b, a & b
            similarity = len(common) / len(union) if union else 0
            if len(common) >= 3 and similarity >= 0.6:
                duplicates.append({"left": left, "right": right, "title_jaccard": round(similarity, 3),
                    "shared_terms": sorted(common), "reason": "Title overlap only; inspect scope, dependencies and implementation before deciding.",
                    "kind": "issue-pr-overlap" if kind != other_kind else "possible-duplicate"})
    recommendations.sort(key=lambda r: (bool(r["gates"]), -r["priority_score"], r["issue"]))
    return {"schema": "xeno.build-scout.report.v1", "observed_at": snapshot["observed_at"],
        "stale": stale, "advisory_only": True, "repositories": repository_summary,
        "recommendations": recommendations, "duplicate_candidates": duplicates,
        "limits": ["No dispatch, claims, writes, closure, merge or runtime authority.",
                   "Coverage is bounded and non-atomic; re-read issues, claims and accepted dependencies before work.",
                   "Closed dependencies are not assumed accepted. Private metadata must remain local.",
                   "Projects, reviews, full CI checks, issue attachments and code contents are not collected."]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        write_private(args.output, analyze(load_snapshot(args.snapshot)))
    except (OSError, ValueError, TypeError, KeyError, RecursionError):
        print("Scout could not analyze input or create a new private report; no source text was logged.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
