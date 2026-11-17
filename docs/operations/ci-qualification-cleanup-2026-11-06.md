---
created: 2026-11-06T09:47:10Z
branch: codex/13-ci-qualification-cleanup
author: patchWERKS / Codex
status: active
---
# Issue 13 qualification workflow cleanup

## Accepted dependency checkpoint

**Observed, coordinator-verified:** [PR 50](https://github.com/patchwerks/furbomek/pull/50)
merged at `2026-11-06T09:44:01Z` into accepted main
`63184419ab5c5437ffc37028ba7829ae53c4f289` after exact-head approval.
The accepted root dependency graph contains Nuxt 4.6.4 and Nitro 2.13.6.
The [security qualification record](nuxt-nitro-security-2026-11-06.md) retains its
original creation time and historical source-specific evidence and pending-state
entries; this later checkpoint records the subsequent merge without rewriting
that history. Merge does not mean runtime deployment or complete remediation.

## Candidate scope

**Proposed:** this separate [issue 13](https://github.com/patchwerks/furbomek/issues/13)
cleanup changes only two workflows, this record and an appended PLAN entry.
It does not incorporate the separate, unmerged PR 51 or grant approval to merge
this cleanup or PR 51.

- The Nuxt/Nitro advisory comparison becomes `workflow_dispatch`-only. Its
  historical baseline remains `6d829351c305a56fb8104469446ae574a07dec7b`; patch-specific
  comparison, lock admission, lint-rule controls and isolation remain unchanged.
  It remains available for explicitly requested historical patch qualification,
  not automatic qualification or promotion of arbitrary future dependencies.
  Manual dispatch qualifies the selected ref at its resolved `github.sha`; the
  recorded candidate SHA must be inspected before attributing a result.
- Regular viewer qualification pins trusted checkout and recorded enforcement
  identity to accepted post-merge `63184419ab5c5437ffc37028ba7829ae53c4f289`.
  Byte-for-byte `cmp` admission covers both root and server manifests and locks.
  This replaces the transitional Nuxt/Nitro Python exception with exact equality
  to the already accepted dependency graph. Future dependency changes require a
  separately reviewed baseline/admission update; this does not automatically
  admit dependency PRs or use a mutable base as trusted enforcement.
- Exact nested Three manifest/lock checks, app path/symlink/size checks and
  accepted `tools/ci` equality remain. Pinned actions/images, constrained
  dependency proxy, offline nonroot read-only execution, resource limits,
  cleanup, bounded evidence export, Node 22/26, real Chromium/Firefox and
  negative typechecking control are retained.

The viewer regression matrix does not replace the historical root build/audit
comparison. That comparison is intentionally no longer automatic on dependency
PRs; a future dependency change needs its own reviewed qualification scope.

The coordinator checked branch protection before preparation: only CodeQL is
required. The historical advisory job is not a required check, so removing its
pull-request trigger does not leave an orphaned required status. No branch
protection setting is changed by this candidate.

## Verification and remaining gates

**Observed static checks:** both workflow YAML files parsed with the installed
Ruby YAML parser; both extracted Bash run blocks passed `bash -n`; all four
Python heredocs compiled in memory without execution. The diff passed whitespace
validation, and this record's relative link resolved. These are syntax/data checks,
not workflow execution or proof of hosted behavior.

**Pending:** fresh hosted viewer qualification and other applicable exact-head
checks, bounded artifact inspection and independent review of this cleanup. Historical PR 50 results do not qualify these workflow
edits. Candidate installations, lifecycle hooks, builds, tests and application
configuration must not execute on the credentialed host. Runtime qualification
belongs in the existing disposable, credential-free hosted workers.

The previously recorded glob and minimatch residual advisories remain unresolved;
deepmerge retains its existing narrow disposition with no expanded risk
acceptance. The prior keyboard file-picker timeout cause remains unresolved;
an unchanged retry passing did not fix it. No advisory dismissal, issue closure,
provider/Hermes/OBS/device access, deployment or live-operation authorization is
included.

Rollback is a separately reviewed revert of these workflow/documentation edits.
It would restore the automatic historical comparison and transitional admission;
it would not revert the accepted PR 50 dependency graph or change any deployed
runtime. Preserve prior evidence when reviewing any rollback.

## Changelog

- 2026-11-06T09:47:10Z: Prepared the bounded post-PR-50 cleanup; static syntax checks passed; hosted checks and independent acceptance remain pending.


## Source qualification, 2026-11-06T09:55:56Z

**Observed:** exact source `ffb2e6c8042172657d9fc7c7816494049a817f87` in
[PR 52](https://github.com/patchwerks/furbomek/pull/52) passed all ten automatic
PR checks, including [non-live verification 42197933782](https://github.com/patchwerks/furbomek/actions/runs/42197933782)
and [CodeQL 42197929510](https://github.com/patchwerks/furbomek/actions/runs/42197929510).
The separately dispatched historical comparison added two successful jobs; those
are not part of the ten-check automatic PR rollup. This source qualification
supersedes the preparation-time hosted-check pending state above, without
rewriting its history or claiming final documentation-head acceptance.

### Viewer regression and exact admission

[Viewer run 42197933777, attempt 1](https://github.com/patchwerks/furbomek/actions/runs/42197933777/attempts/1)
passed on Node 22.22.3/npm 10.9.8 and Node 26.7.0/npm 11.19.0 with enforcement
`63184419ab5c5437ffc37028ba7829ae53c4f289`. Each runtime passed 66 unit tests,
16-file targeted authoring lint with zero errors/warnings/fatal errors, root and
viewer preparation, normal typechecking, static generation, and the negative
control: the injected draw mutation failed with `app.vue(35,34)` TS2339 and the
restored source passed. Chromium 156.0.8078.4 and Firefox 157.0 each passed all
43 browser cases on both Node versions, including keyboard file import and the
builder download/reimport/CLI metadata roundtrip: four successful configurations.

All four browser records contain empty outbound-request and error arrays. These
accepted tests do not collect CSP/console diagnostics, so these results do not
establish absence of CSP or console messages. The old picker-timeout cause
remains unresolved; this passing run does not demonstrate its repair. Application
and test bytes are identical to accepted PR 50; no new screenshot visual review
was performed or claimed for this workflow-only change. Client static generation
under `ssr:false` does not establish server-rendered content or live deployment.

### Explicit manual historical comparison

[Comparator run 42197971669, attempt 1](https://github.com/patchwerks/furbomek/actions/runs/42197971669/attempts/1)
was explicitly dispatched on this cleanup branch at the same exact source SHA.
Node 22 job `127825909565` and Node 26 job `127825909709` succeeded against
historical baseline `6d829351c305a56fb8104469446ae574a07dec7b`. Both report
`persisted` mode and lock SHA-256
`8fcda3cd6ef3b23dc4aad02e18a5be400d3697cea981d688bb29e536635f4ef0`, with
all 14 non-Nuxt direct versions unchanged.

Both baseline/candidate variants passed normal preparation, node-server builds,
types and the full offline root lifecycle, including root postinstall
prepare/build and nested server installation. Node 26 retains the npm
`allowScripts` warning for the blocked esbuild dependency postinstall; successful
root lifecycle is not evidence that every dependency hook executed. App and
repository lint each have zero errors/warnings/fatal errors. Malformed Vue/TS
controls each produced a fatal parser error, self-import and constant-condition
controls remained errors, dependency trees had no problems, effective Vue/TS
rule-change arrays were empty, and inspector/comparison completed. ESLint is
10.14.0.

Both runtimes report 28 baseline npm package findings (25 moderate, 3 low) and
27 candidate findings (20 moderate, 7 low), with no high/critical findings.
These are package findings, not GitHub security-alert counts or counts of distinct
advisories. The same three direct advisory identities remain: glob
`GHSA-3g3m-2fjr-6pw4`, minimatch `GHSA-g3hv-75wg-m249` and deepmerge
`GHSA-gcqx-w48m-w2h4`. This cleanup does not complete remediation or expand the
existing narrow deepmerge disposition.

### Artifact provenance and final-head boundary

The coordinator independently verified all four official ZIP digests and source
identities after bounded inert inspection. Official run/repository identity and
nonexpiry were checked; unique allowlisted regular entries stayed within 8 MiB
per file and 32 MiB per job, with no symlink or path-indirection admission.
Viewer archives contain 39 files each and comparator archives 38 each. Embedded
candidate identities match the exact source above; viewer enforcement matches
`63184419...`, while comparator baseline matches `6d829351...`.

| Artifact | Official ZIP SHA-256 |
|---|---|
| Viewer Node 26 / [13492812740](https://api.github.com/repos/patchwerks/furbomek/actions/artifacts/13492812740) | `c17a7b7b84ae6367f017b9cef1a672111ef77ab78033d9ccb6b04cd0f6fed662` |
| Viewer Node 22 / [13492334522](https://api.github.com/repos/patchwerks/furbomek/actions/artifacts/13492334522) | `da1719b5f0e4ce1a27118890d6325b19fd4030b6ae637aebf42308ca974981f6` |
| Manual comparator Node 22 / [13493355906](https://api.github.com/repos/patchwerks/furbomek/actions/artifacts/13493355906) | `a1c2951dc66869fd08558d71b3948843a81ffb288b4b4aa389a96138d500e3a9` |
| Manual comparator Node 26 / [13492607860](https://api.github.com/repos/patchwerks/furbomek/actions/artifacts/13492607860) | `081f9f3f6776c1e6726b32fff89330f9ccdfe1f6f14e9bbeae1fc46fecd61f94` |

Static comparison confirms the historical workflow's permissions and complete
jobs remain byte-identical to accepted main, and the viewer provisioning,
execution and evidence-export tail is unchanged except for its enforcement SHA.
No candidate code or artifact code ran on the credentialed host.

**Still pending:** automatic checks for the final documentation-only child and
independent exact-head review of PR 52. This evidence appendix changes only PLAN
and this record; workflow, source, tests and dependency bytes remain identical
to the qualified source. Another manual comparison is not required for that
unchanged workflow: the recorded manual run remains bound to `ffb2e6c...`, while
fresh automatic final-head checks and the documentation-only diff establish the
separate final-head boundary. Any later executable change requires reassessment.
No result here merges PR 52 or PR 51, closes issue 13, dismisses an advisory,
authorizes new risk acceptance, deploys a runtime or grants live access.

### Source-evidence changelog

- 2026-11-06T09:55:56Z: Appended verified source viewer, manual comparator and automatic-check evidence, artifact provenance and remaining final-head/independent-review gates.
