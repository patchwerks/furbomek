---
timestamp: 2026-10-29T19:06:06Z
branch: codex/13-update-activity-pytest
author: Codex security subagent
status: proposed; not deployed
---

# Activity pytest compatibility evidence — 2026-10-30

This bounded #13 slice updates the Hermes activity test runner from locked
pytest **8.4.2** to **9.1.1**, based on published main
`9347304e866ca90e8eec2d85f3bd3c41002d9a42`. No runtime or test changes were needed.

## Version selection

The [reviewed advisory](https://github.com/advisories/GHSA-6w46-j5rx-g56g)
identifies versions before 9.0.3 as affected by insecure temporary-directory
handling. The [upstream 9.0.3 release](https://github.com/pytest-dev/pytest/releases/tag/9.0.3)
and [fix](https://github.com/pytest-dev/pytest/pull/14343) confirm the repair.
The [9.1.1 release](https://github.com/pytest-dev/pytest/releases/tag/9.1.1)
includes later bug fixes, including fixture parametrization and initial conftest
loading corrections. It is the deliberately bounded candidate already exercised
by this repository's gateway validation; activity compatibility is checked here.

9.1.1 is **not** the newest release: upstream has announced
[9.2.0](https://docs.pytest.org/en/stable/announce/release-9.2.0.html).
The newer release's configuration/parametrization changes are outside this
qualification. The manifest now requires `pytest>=9.0.3,<10`, excluding the known
affected versions; the lock selects exactly 9.1.1. Future lock refreshes still
need compatibility checks rather than assuming every allowed version is tested.

## Exact change boundary

`uv 0.11.7 lock --upgrade-package pytest==9.1.1` regenerates the lock while
retaining other selections. Only pytest's version/artifacts and the project's
dev requirement change: zero packages added/removed, and every other dependency
object is identical. Lock revision 3 is unchanged.

- Python remains `>=3.12,<3.13`; Pillow remains **12.3.0** from main. The separate
  Pillow proposal is not included.
- All 60 collected test IDs and all test files are unchanged. There are no new
  skips, deletions, xfails, filtered failures, or weakened expectations.
- `--strict-config`, `--strict-markers`, warning-as-error, `minversion`, testpaths,
  and all lint/type settings are unchanged.
- Capture remains default OFF and the live desktop policy remains rejected.
  The existing autouse fixture that fails real desktop capture is unchanged.

## Executed local checks

Separate baseline/candidate environments used Python **3.12.14** on macOS arm64,
uv **0.11.7**, and frozen wheel-only installs (`uv sync --frozen --no-build`).
Tests ran in an owner-only disposable temporary directory with an empty
credentials environment, network denied, user-home/device access denied, and
WindowServer service lookup denied. Fixtures and subprocess inputs are synthetic.
No desktop/camera capture, live Hermes/OBS service, provider call, or hardware
access occurred.

| Gate | Baseline 8.4.2 | Candidate 9.1.1 |
| --- | --- | --- |
| `python -m pytest --collect-only -q` | 60 IDs | same 60 IDs |
| `python -m pytest -q` | 60 passed | 60 passed |
| `ruff check .` | passed | passed |
| `ruff format --check .` | passed | passed |
| `basedpyright` | 0 errors/warnings/notes | 0 errors/warnings/notes |
| `uv lock --check --offline` | passed | passed |

These existing tests retain observer-to-spool-to-broker subprocess coverage,
cursor/checkpoint consistency, redaction, TTL/failure handling, and capture-policy
refusal. Logs, the exact collected-ID list, dependency comparison, and worker
profile are retained in the private review evidence. Independent review and
hosted check results are reported on the PR separately from these local checks.

## Limits and rollback

Passing the suite establishes compatibility; it is not by itself a reproduction
of the temporary-directory vulnerability. No live capture, hardware, deployment,
operating-system matrix, or Godot consumer acceptance was performed. This does
not close the wider #13 issue or activate the separate CI/bootstrap proposals.
Revert the manifest and lockfile together and recreate the prior frozen
environment to roll back this slice.
