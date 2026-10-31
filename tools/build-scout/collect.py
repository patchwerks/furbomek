#!/usr/bin/env python3
"""Trusted, explicit GitHub GET collection. Keep separate from candidate execution."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from scout import ISSUE_URL, REPOSITORIES, SCHEMA, canonical, clean, write_private

PAGE_SIZE = 30
MAX_RESPONSE_BYTES = 4 * 1024 * 1024
PATH = re.compile(r"repos/(patchwerks/(?:patchwerks|furbomek|jabberwerk))(?:(?:/issues|/pulls|/actions/runs)|/issues/[1-9]\d*/(?:comments|dependencies/blocked_by))?\Z")


class ReadFailure(Exception):
    """Contains a fixed public-safe category, never raw API/CLI output."""


class GitHubReadOnly:
    def __init__(self, repositories: list[str], max_requests: int = 120):
        if not repositories or set(repositories) - set(REPOSITORIES):
            raise ValueError("Unsupported repository")
        if not 1 <= max_requests <= 200:
            raise ValueError("Invalid request budget")
        self.repositories = frozenset(repositories)
        self.remaining = max_requests

    def get(self, path: str, params: dict[str, str | int]) -> object:
        match = PATH.fullmatch(path)
        if not match or match.group(1) not in self.repositories:
            raise ValueError("Read endpoint is not allowlisted")
        for name, value in params.items():
            valid = ((name == "page" and type(value) is int and 1 <= value <= 5)
                     or (name == "per_page" and value == PAGE_SIZE)
                     or (name == "state" and value == "all")
                     or (name == "sort" and value == "updated")
                     or (name == "direction" and value == "desc"))
            if not valid:
                raise ValueError("Query is not allowlisted")
        if self.remaining == 0:
            raise ReadFailure("request-budget-exhausted")
        self.remaining -= 1
        command = ["gh", "api", "--hostname", "github.com", "--method", "GET", path,
                   "-H", "Accept: application/vnd.github+json", "-H", "X-GitHub-Api-Version: 2022-11-28"]
        for key, value in sorted(params.items()):
            command += ["-f", f"{key}={value}"]
        # gh alone uses the operator's credentials. No issue content enters argv/env.
        environment = dict(os.environ)
        environment.pop("GH_DEBUG", None)
        environment.update(GH_HOST="github.com", GH_PROMPT_DISABLED="1", GH_PAGER="cat", GIT_TERMINAL_PROMPT="0")
        try:
            result = subprocess.run(command, stdin=subprocess.DEVNULL, capture_output=True,
                                    timeout=30, check=False, env=environment)
        except (OSError, subprocess.TimeoutExpired):
            raise ReadFailure("transport-or-cli-unavailable") from None
        if result.returncode:
            code = re.search(rb"HTTP (401|403|404|429|500|502|503)", result.stderr)
            raise ReadFailure("http-" + code.group(1).decode() if code else "request-failed")
        if len(result.stdout) > MAX_RESPONSE_BYTES:
            raise ReadFailure("response-too-large")
        try:
            return json.loads(result.stdout)
        except (ValueError, RecursionError):
            raise ReadFailure("invalid-json") from None


def pages(reader: GitHubReadOnly, path: str, *, max_pages: int, key: str | None = None,
          params: dict | None = None) -> tuple[list[dict], dict]:
    if not 1 <= max_pages <= 5:
        raise ValueError("Page bound must be between one and five")
    collected = []
    for page in range(1, max_pages + 1):
        try:
            result = reader.get(path, {**(params or {}), "per_page": PAGE_SIZE, "page": page})
            batch = result.get(key) if key and isinstance(result, dict) else result
            if not isinstance(batch, list) or len(batch) > PAGE_SIZE or any(not isinstance(i, dict) for i in batch):
                raise ReadFailure("invalid-page-shape")
        except ReadFailure as error:
            return collected, {"status": "unavailable" if not collected else "partial", "reason": str(error), "pages_read": page - 1}
        collected.extend(batch)
        if len(batch) < PAGE_SIZE:
            return collected, {"status": "complete", "pages_read": page, "items": len(collected)}
    return collected, {"status": "partial", "reason": "page-cap-reached", "pages_read": max_pages, "items": len(collected)}


def issue_record(raw: dict) -> dict:
    number = raw.get("number")
    if type(number) is not int or number < 1 or raw.get("state") not in ("open", "closed"):
        raise ValueError("Invalid issue record")
    if not isinstance(raw.get("title"), str) or (raw.get("body") is not None and not isinstance(raw["body"], str)):
        raise ValueError("Invalid issue text")
    for field, key in (("labels", "name"), ("assignees", "login")):
        if not isinstance(raw.get(field), list) or any(not isinstance(x, dict) or not isinstance(x.get(key), str) for x in raw[field]):
            raise ValueError("Invalid issue ownership or labels")
    return {"number": number, "node_id": clean(raw.get("node_id"), 128),
            "title": clean(raw.get("title"), 512), "body": clean(raw.get("body")),
            "body_truncated": isinstance(raw.get("body"), str) and len(raw["body"]) > 20000,
            "state": raw["state"], "state_reason": clean(raw.get("state_reason"), 64),
            "updated_at": clean(raw.get("updated_at"), 64),
            "labels": [clean(x.get("name"), 128) for x in raw.get("labels", []) if isinstance(x, dict)],
            "assignees": [clean(x.get("login"), 128) for x in raw.get("assignees", []) if isinstance(x, dict)]}


def collect(reader: GitHubReadOnly, repositories: list[str], max_pages: int = 2) -> dict:
    snapshot = {"schema": SCHEMA, "observed_at": datetime.now(timezone.utc).isoformat(), "repositories": {}}
    for repo in repositories:
        canonical(repo)
        base = "repos/" + repo
        data = {"metadata": {}, "issues": [], "pulls": [], "runs": [], "coverage": {}}
        snapshot["repositories"][repo] = data
        coverage = data["coverage"]
        try:
            meta = reader.get(base, {})
            if not isinstance(meta, dict) or not isinstance(meta.get("full_name"), str) or meta["full_name"].lower() != repo:
                raise ReadFailure("invalid-repository-metadata")
            data["metadata"] = {"id": meta.get("id"), "private": meta.get("private"),
                                "default_branch": clean(meta.get("default_branch"), 256), "archived": meta.get("archived")}
            coverage["metadata"] = {"status": "complete"}
        except ReadFailure as error:
            coverage["metadata"] = {"status": "unavailable", "reason": str(error)}
            for source in ("issues", "pulls", "runs"):
                coverage[source] = {"status": "unavailable", "reason": "metadata-unavailable"}
            continue
        for kind, endpoint in (("issues", "issues"), ("pulls", "pulls"), ("runs", "actions/runs")):
            raw, coverage[kind] = pages(reader, base + "/" + endpoint, max_pages=max_pages,
                key="workflow_runs" if kind == "runs" else None,
                params={} if kind == "runs" else {"state": "all", "sort": "updated", "direction": "desc"})
            for item in raw:
                if kind == "issues" and "pull_request" in item:
                    continue
                try:
                    if kind == "runs":
                        if type(item.get("id")) is not int or item["id"] < 1:
                            raise ValueError("Invalid run")
                        fields = {"status": 64, "conclusion": 64, "head_sha": 64, "head_branch": 256, "updated_at": 64}
                        if any(item.get(name) is not None and not isinstance(item[name], str) for name in fields):
                            raise ValueError("Invalid workflow metadata")
                        data[kind].append({"id": item["id"], **{
                            name: clean(item[name], limit) if item.get(name) is not None else None
                            for name, limit in fields.items()}})
                    else:
                        record = issue_record(item)
                        if kind == "pulls":
                            record["head_sha"] = clean((item.get("head") or {}).get("sha"), 64)
                            record["draft"] = item.get("draft") is True
                        data[kind].append(record)
                except (ValueError, TypeError, AttributeError):
                    coverage[kind] = {"status": "partial", "reason": "malformed-item"}
        for issue in data["issues"]:
            if issue["state"] != "open":
                continue
            number = issue["number"]
            for name, suffix in (("comments", "comments"), ("blockers", "dependencies/blocked_by")):
                raw, coverage[f"issue:{number}:{name}"] = pages(reader, f"{base}/issues/{number}/{suffix}", max_pages=max_pages)
                issue[name] = []
                for entry in raw:
                    if name == "comments":
                        if type(entry.get("id")) is not int or entry["id"] < 1 or not isinstance(entry.get("body"), str):
                            coverage[f"issue:{number}:{name}"] = {"status": "partial", "reason": "malformed-comment"}
                            continue
                        issue[name].append({"id": entry["id"], "body": clean(entry["body"]),
                                            "body_truncated": len(entry["body"]) > 20000,
                                            "updated_at": clean(entry.get("updated_at"), 64)})
                    else:
                        url = clean(entry.get("html_url"), 1024)
                        if not ISSUE_URL.fullmatch(url) or entry.get("state") not in ("open", "closed"):
                            coverage[f"issue:{number}:{name}"] = {"status": "partial", "reason": "malformed-blocker"}
                            continue
                        issue[name].append({"url": url, "state": entry["state"],
                                            "state_reason": clean(entry.get("state_reason"), 64)})
    snapshot["collection_finished_at"] = datetime.now(timezone.utc).isoformat()
    return snapshot


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", choices=REPOSITORIES, action="append", required=True)
    parser.add_argument("--max-pages", type=int, choices=range(1, 6), default=2)
    parser.add_argument("--max-requests", type=int, default=120)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        repositories = list(dict.fromkeys(args.repo))
        snapshot = collect(GitHubReadOnly(repositories, args.max_requests), repositories, args.max_pages)
        write_private(args.output, snapshot)
    except (OSError, ValueError, TypeError, KeyError, RecursionError):
        print("Collection could not create a new private snapshot; no source text or credentials were logged.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
