---
created: 2026-11-05T08:13:11Z
branch: codex/32-pack-metadata
author: patchWERKS / Codex
status: active
---
# Presentation metadata preparation

**Metadata/core source qualified; combined integration and acceptance pending.** Linked work is
[issue 32](https://github.com/patchwerks/furbomek/issues/32), under the
[parallel authoring claim](https://github.com/patchwerks/furbomek/issues/32#issuecomment-6653015423).
Preparation base is accepted main
`c0c3f7ce44cfa3db34cbe46a723bf1fc16b56b6c`; accepted coordination policy remains
`patchwerks/patchwerks@b99937e5f22ff34455723aaca667b394bd2be86e`.

## Scope and proof

The separate `tools/presentation-pack/` implementation owns strict companion
metadata parsing, explicit bounded file input, and the frozen `validate` and
`template` CLI. The core parser, pack schema, runtime, declarations, manifests,
existing workflows and viewer were not changed by this slice. See the
[format and limitations](../contributing/presentation-metadata.md).

**Observed preparation checks:** `node --check` accepted all four new `.mjs`
files (including tests); source inspection confirmed exact CLI paths, same-read
parse/hash, descriptor closure, no production file writes, and the accepted
starter workflow's pins/isolation pattern. `git diff --check` reported no
tracked whitespace errors. New files were additionally reviewed as source.
No candidate module, CLI, test, package installation or build ran on the host.
Syntax inspection is not runtime evidence.

**Pending:** root boundary review before execution; credential-free hosted
Node 22/26 metadata and existing core suite; combined builder download and
companion/tamper integration; exact published-head checks; independent review
and policy acceptance. Issue 32 remains open. No claim of completed acceptance
or deployed tooling follows from this record.

The test source exercises both licenses, Unicode public names, strict size and
encoding limits, malformed JSON and duplicate decoded keys, field/type/nesting
rejections, digest/compatibility mismatches, symlink/FIFO/directory/oversize
rejections, injected descriptor open/read/path races and unsupported flags,
handle closure, CLI status/output channels, terminal-safe filenames and absence
of output writes. The injected descriptor cases are unit boundary checks;
actual filesystem cases and the browser download integration provide separate
surfaces. No privileged adversarial filesystem snapshot guarantee is claimed.

## Candidate worker boundary

New `.github/workflows/presentation-pack-tools.yml` is advisory. It copies the
accepted starter's action and Node image pins, exact-head checkout without
persisted credentials, bounded regular-file mount inspection, and 10-minute
job timeout. Only `tools/presentation-pack` and `packages/extension-preview`
are bind-mounted read-only. The worker has no network, inherited environment,
Git directory, host home, credentials, Docker socket or host-device mount; it
runs as UID 1000 with dropped capabilities, no-new-privileges, read-only root,
2 CPUs, 1 GiB memory, 128 PIDs and a 512 MiB temporary filesystem. No install
step or dependency change is included. The proposed workflow cannot approve
its own trust boundary; root and independent review remain necessary.

After review, the candidate worker command is:

```sh
node --experimental-vm-modules --test tools/presentation-pack/tests/*.test.mjs packages/extension-preview/tests/*.test.mjs
```

The shell expands these fixed test globs only in the disposable worker. The
production CLI never expands paths or discovers files. Preserve timestamps and
append dated evidence with exact commit, run, matrix results and limitations
when real checks finish. Root owns publication/acceptance and will combine this
slice with the separately owned builder changes in one PR.

## Rollback and exclusions

Before acceptance this is source preparation only. Reverting the new tools,
workflow and two metadata documents removes the entire feature, leaving packs
and the unchanged core intact. Existing companions remain inert JSON. No
installation, device, media, live transport, host configuration or power change
occurred. Parent-directory trust and self-declared author/license limitations
remain intentional and documented.


## First hosted pass and focused correction, 2026-11-05

**Observed failed first pass:** source
`41b923288ba8097e3a892b9b240e1e8479069527` ran in
[run 41993762135](https://github.com/patchwerks/furbomek/actions/runs/41993762135).
Node 22.22.3 and 26.7.0 each passed 86 of 87 metadata/core tests. The sole
failure was the CLI usage test: its duplicate `--json` case incorrectly
required `Usage` on stderr. The CLI correctly returned exit 2, structured
stdout with `error: "usage"`, and empty stderr, as documented. This failed
first pass is not runtime acceptance of the full suite.

At 2026-11-05T08:23:12Z, the test was corrected to assert structured stdout
(`ok: false`, `error: "usage"`, usage message) and empty stderr when the
malformed invocation includes `--json`; all other usage cases assert the
usage message on stderr and empty stdout. All existing exit-2 cases remain.
Production CLI logic was unchanged. The new advisory workflow job display
names changed to `metadata-node22` / `metadata-node26` to distinguish them
from the existing starter advisory jobs; pins and worker boundary are unchanged.

**Pending after correction:** fresh hosted matrix on the published correction,
combined browser-download integration, exact-head checks and independent
acceptance. No candidate code or tests were executed on the host. The earlier
preparation-only pending list is historical; the first hosted execution is
recorded here without implying successful completion or issue 32 closure.


**Additional first-pass diagnostic, 2026-11-05:** the combined viewer
[run 41993761735](https://github.com/patchwerks/furbomek/actions/runs/41993761735)
reported two `no-control-regex` lint errors in the metadata test's terminal
output assertions. Those assertions now check explicitly for absence of code
points U+001B and U+202E in the same output channels instead of embedding a
control character escape in a regular expression. No lint rule was suppressed,
and the terminal-safety coverage and earlier usage-channel correction remain.
This correction awaits the same fresh hosted run; it was not executed on host.


## Corrected metadata source qualification, 2026-11-05

**Observed:** [run 41994352925](https://github.com/patchwerks/furbomek/actions/runs/41994352925)
completed successfully at 2026-11-05T08:26:03Z for exact source
`1a0e5ae66e4ffe28c7cdc2c03860cae2f97ced38`. The GitHub run/status JSON confirms
that head and successful completed jobs; raw logs confirm actual runtime
versions and totals, rather than inferring them from the workflow matrix.

| Job | Observed Node | Tests | Passed | Failed / cancelled / skipped / todo |
| --- | --- | --- | --- | --- |
| metadata-node22 | 22.22.3 | 87 | 87 | 0 / 0 / 0 / 0 |
| metadata-node26 | 26.7.0 | 87 | 87 | 0 / 0 / 0 / 0 |

Both logs explicitly report successful CLI template/match/absent/tampering/no
output-write checks and CLI usage/file-failure/terminal-safety checks. The
strict parser, descriptor race/file boundaries and unchanged core suites also
passed. VM Modules emitted its expected experimental-feature warning; that is
not a lint result or evidence for arbitrary runtimes.

The raw read-only provider response and logs were retrieved at
2026-11-05T08:28:09Z. Retained sibling evidence has SHA-256:

- Run JSON: `4bf28f84535974fb249d143bcfcea0c54043452e8144347c5c3887f4332d4e57`.
- Run log: `6a495652a41ad35c5fead8c084c7312a8646c8124835b9cbd65d71c5559db206`.

This supersedes the corrected metadata suite's pending rerun status above;
the first-pass 86/87 failure and two lint-fixture errors remain recorded as
historical evidence. No candidate code or downloaded artifact was executed on
the host. Source qualification is bounded to this exact revision and these
offline Node workers. Combined browser-download integration also passed in
[viewer run 41994353036](https://github.com/patchwerks/furbomek/actions/runs/41994353036)
at the same exact source: all four Chromium/Firefox build combinations passed
real export/reimport, CLI template/match and byte-tamper rejection. See the
[builder evidence](pack-builder-2026-11-05.md) for artifact provenance and visual
review. Final published head checks, independent review and policy acceptance
remain pending. A later
source change requires fresh applicable evidence. Issue 32 remains open.
