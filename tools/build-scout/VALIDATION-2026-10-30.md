# Build Scout validation — 2026-10-30

Work: [furbomek issue 14](https://github.com/patchwerks/furbomek/issues/14).
Branch: `work/14-build-scout`. Dates use the operator's Asia/Bangkok timezone.

## Observed verification

- All 30 synthetic tests passed under Python 3.14.7 using
  `python3 -m unittest discover -s tools/build-scout -p 'test_*.py' -v`.
- The worker had a temporary HOME, no credential environment, denied network,
  host-home and device access, read-only source and temporary-only writes.
- Actual collection used a separate credential-holding, allowlisted GET-only
  bridge. The candidate collector could request only the reviewed bounded reads;
  it could not access credentials or arbitrary network endpoints.
- All 48 actual API GET calls succeeded. Collection and offline analysis exited
  successfully. Every requested source page reported complete coverage in this
  bounded observation; this is not a permanent or organization-wide completeness
  claim. The files below matched the source hashes used for verification.

The original credential-bearing `gh` subprocess was not executed directly inside
the candidate worker. Mocked subprocess tests verify its explicit method/path,
budget, timeout and error behavior; the separate bridge verifies actual provider
responses and the collector/analyzer logic. Other operators' CLI installations,
authentication and provider permissions remain environment-specific.

## Public-safe observations

The Furb-o-Mek snapshot contained 12 issues, eight PRs and 18 workflow runs at
collection time. Its report retained the actual dependency references for
[issue 7](https://github.com/patchwerks/furbomek/issues/7) and physical gates for
[issue 9](https://github.com/patchwerks/furbomek/issues/9) and
[issue 10](https://github.com/patchwerks/furbomek/issues/10).

The initial provider run exposed a real classification defect: the explicit
"None" dependency sections in [issue 2](https://github.com/patchwerks/furbomek/issues/2)
and [issue 4](https://github.com/patchwerks/furbomek/issues/4), followed by ordinary
explanatory prose, were incorrectly classified as dependencies. Public-text
regressions now preserve that distinction. The second provider run left those
issues gated only by their observed existing owners/claims; it did not invent a
dependency. Unresolved prose still requires review, and native/linked dependencies
retain their acceptance gate.

The report included PR head revisions and same-SHA workflow observations. A title
overlap between governance-adoption PRs was reported only as a heuristic candidate;
it did not close, assign or otherwise change anything. Private repository counts,
titles, bodies and collection outputs are deliberately absent from this record.

## Verified source hashes (SHA-256)

| File | Hash |
|---|---|
| `collect.py` | `d0c117f3041c7c7b05b4e1bd3b3e700525907716aa424ca016d1f9484c2f8f37` |
| `scout.py` | `b388e8e403e0075ff5a6dd48b14223f62c5b0a86715eb45dbcbc8a0efd774f57` |
| `test_scout.py` | `58b9387bbe57da1cbb4e342f0608c8611bb444155bdf2628e2d41de1281bf9f8` |

## Limits and rollback

No collection snapshot or report is a dispatch authority or current readiness
certificate. Results are non-atomic, time-bound and access-scoped. Current claims,
private Project state, reviewed dependencies and acceptance must be reconciled
before work. A workflow with the same SHA does not prove the required workflow,
event, review, branch protection or acceptance context.

No hardware, live media, deployment, merge or repository write was performed by
Scout. Independent review and hosted verification of the final branch remain
separate gates. This tool has no persistent daemon or configuration installation;
rollback is to stop invoking it and return to the previously reviewed source.
