# Build Scout

Read-only GitHub intelligence for [issue 14](https://github.com/patchwerks/furbomek/issues/14).
Scout creates an evidence-linked advisory report; GitHub Issues and the shared
Project retain task identity, acceptance and dispatch authority. This is tooling
for inspecting the work in [PLAN.md](../../PLAN.md), not another work queue.

## Two separate boundaries

1. A trusted operator reviews `collect.py`, then explicitly collects selected
   repositories using an existing GitHub CLI login. Every request uses an
   allowlisted `github.com` REST path, explicit GET, a 30-second timeout, bounded
   pages and a global request budget. It never invokes a shell or follows URLs
   supplied by an issue. No GitHub writes are implemented.
2. `scout.py` analyzes the snapshot offline with standard-library Python 3.10+.
   Run candidate code and tests on disposable credential-free workers with no
   network, host-home or device access. A clean environment alone is not device
   isolation. The analyzer does not import the collector or execute issue text.

An agent operating the trusted collector can use these commands after selecting
an existing private output directory outside every Git checkout. Output paths
must be new; exclusive file creation uses mode 0600 and refuses overwrites and
existing symlinks. These example paths are operator-chosen placeholders, not
instructions to use a live host or private service:

```sh
python3 tools/build-scout/collect.py --repo patchwerks/furbomek \
  --repo patchwerks/patchwerks --max-pages 2 --max-requests 120 \
  --output /private-output/scout-snapshot.json
python3 tools/build-scout/scout.py /private-output/scout-snapshot.json \
  --output /private-output/scout-report.json
```

`--repo patchwerks/jabberwerk` is also supported when explicitly selected and
authorized. Repository existence/readability is never inferred from a failed
request. A 404 can mean missing source or unavailable access. No credential is
accepted as a command-line argument. CLI stderr is reduced to fixed error
categories; raw errors are never saved. Credentials remain with the trusted
collector, never the offline worker.

## Evidence and limits

The snapshot records collection start/end, repository IDs/default branch/privacy,
bounded recently updated issues and PRs (open and closed), PR head revisions,
recent workflow runs, and native blockers/comments for collected open issues.
Each source has complete, partial or unavailable coverage. A full final page is
conservatively partial; the tool does not pretend a cap proves exhaustion.
Default limits are 30 records/page, two pages/source and 120 requests total;
maximums are five pages/source and 200 requests. GitHub issues pages include PRs,
which are filtered from the issue collection. Collection is not an atomic view.

Recommendations link to canonical issues. Unavailable coverage, truncated bodies,
snapshots older than 24 hours or over five minutes in the future, native/prose
blockers, physical labels, assignees and claim comments gate recommendations.
Claim releases require reconciliation; Scout never expires a claim. Closed
dependencies are not assumed accepted, including closed-as-not-planned work.
Ranking puts ungated review candidates first, then awards 20 points for an
observed `ready-for-agent` label and 10 for `area:verification`; reasons are shown.
Labels and issue prose are untrusted evidence, never authorization. Always inspect
the current plan, claim, native dependencies, acceptance and private Project
before work. Scout does not read Project state or certify readiness.

Duplicate candidates use case-folded title word overlap, excluding common words:
at least three shared terms and Jaccard similarity >= 0.6. Reports show shared
terms and the score, including issue/PR overlaps. Closed/closed pairs are skipped.
This is an explainable heuristic, not semantic identity, proof of implementation
or a reason to close anything automatically.

CI output names observed failed/cancelled workflow run URLs and their head SHAs.
It does not equate latest runs with current PR heads or enumerate all required
checks, external statuses, reviews, branch policy or security alerts. No green
merge/deploy verdict is emitted. Code contents, attachments and logs are not read.

Snapshots/reports are local private data even for a public repository: arbitrary
issue text can contain private information. Common credential patterns are
removed, but this is not a comprehensive secret scanner or publication filter.
Do not commit snapshots/reports or automatically post them to public issues.
Re-read provider evidence after collection before any independently authorized
action. No speech engine, Hermes planner, OBS controller, robot adapter or new
runtime authority is introduced.

## Offline verification

Inside the isolated worker, from this directory:

```sh
python3 -m unittest -v test_scout.py
```

The synthetic suite exercises pagination, partial/unavailable sources, request
budget, endpoint/method restrictions, error redaction, dependencies, physical and
claim gates, stale data, duplicate explanations, hostile text, CI provenance,
private output permissions and an actual offline CLI round trip. No provider or
live integration qualification is implied. Independent review is required.

Observed verification on 2026-10-29: all 22 offline tests passed under Python
3.14.7 in a worker with a temporary HOME, no credential environment, denied
network/devices/host-home access, read-only source and temporary-only writes.
The actual invocation from the repository root was
`python3 -m unittest discover -s tools/build-scout -p 'test_*.py' -v`.
The credential-bearing live collector has not been exercised. Provider API
qualification and independent review remain pending; passing mocked transport
tests does not prove access or acceptance against a live repository.

API references: [GitHub CLI GET arguments](https://cli.github.com/manual/gh_api),
[native issue dependencies](https://docs.github.com/en/rest/issues/issue-dependencies).
