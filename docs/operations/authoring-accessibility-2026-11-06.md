---
created: 2026-11-06T08:12:22Z
branch: codex/32-authoring-accessibility
author: patchWERKS / Codex
status: active
---
# Pack authoring keyboard and diagnostic follow-up

Canonical task: [issue 32](https://github.com/patchwerks/furbomek/issues/32).
Preparation base is accepted main
`6d829351c305a56fb8104469446ae574a07dec7b` (PR 49), following accepted
pack-authoring PR 48 merge `e19297fa04bbbf30f0cfe60bc48de0e847011549`.
This record describes a new bounded candidate. It preserves the historical
[builder evidence](pack-builder-2026-11-05.md) and
[metadata evidence](presentation-metadata-2026-11-05.md); it does not promote
their results to proof for this changed source.

## Source changes and design audit

The existing Bootstrap workbench, system typography, theme colors, spacing and
focus treatment are retained. Builder selects use native appearance and remove
Bootstrap's background image so their chevron does not require a data URI.
The CSP, dependencies and asset inventory are unchanged. No imagery is selected
or generated, and the original six-legged procedural geometry is unchanged.

Cue rows receive stable UI-only identity in a WeakMap. Labels and control IDs
remain associated as rows move. Adding a cue focuses its time field after
rendering. Removing the row containing focus moves focus to the next editable
cue time, otherwise the previous editable cue time, otherwise Add cue. Removing
another row preserves the surviving focused control and its value. UI identity
is not added to drafts or exported packs.

Builder error and valid-status regions remain mounted and atomic, with mutually
exclusive text. Editable controls associate their validation description with
the error region. The visual playback clock explicitly has `aria-live="off"`
to avoid per-frame live updates; the keyboard timeline retains accessible
millisecond value text. These are DOM semantics, not evidence of actual
screen-reader announcement behavior.

CLI filesystem error codes map to fixed useful messages that omit raw paths.
Unknown coded failures receive a generic read-error message. Uncoded validation
messages retain detail through the existing terminal-safe JSON serialization;
stacks are not printed. Exit statuses and output channels remain unchanged.
The bounded filesystem reader, parser, timeline schema, exact-byte export,
locked reset, stale-read protection and live-authority boundaries are unchanged.

## Acceptance surface and pending execution

**Prepared, not yet executed:** the browser matrix retains all 43 prior cases
and adds keyboard Add/Remove focus, stable surviving DOM identity and values,
persistent atomic error/status mutations, clock semantics and actual console/CSP
capture. The prepared browser inventory contains 54 cases; this is an expected
inventory, not a pass count. Node and Chromium/Firefox coverage continues through
the existing credential-free disposable hosted workers, with candidate execution
offline and no credentials, production-network or device access.

Reflow checks at 640 and 320 CSS-pixel viewport widths are layout equivalents for
reduced available width. They do not operate browser zoom and must not be
reported as actual 200%/400% browser-zoom tests. Screenshots, computed native
select appearance, visible focus and error-state rendering require review of
the resulting artifacts.

CLI regressions cover actual missing pack/metadata/template paths, a non-directory
path component, actual unreadable POSIX files, and injected expected/unknown
filesystem codes. Both JSON and plain output must retain useful diagnostics,
correct channels/statuses, terminal safety and no raw failure-path leakage.
The permission fixture skips root and Windows; the hosted unprivileged POSIX
worker is expected to exercise it. Existing file-boundary and strict-parser
regressions remain required.

**Observed during preparation:** source and diff inspection plus a clean
`git diff --check`. No candidate code, tests, build, dependency installation or
browser was executed on the credentialed host. Exact-source hosted results,
artifact provenance, visual review, final-head checks and independent acceptance
remain pending. No full accessibility, screen-reader, GPU, arbitrary-browser,
rights, installation, physical, live-operation, deployment or merge claim follows.

## Native file-picker history and diagnostic limits

Historical PR 50 source `a4dfd3dd2358de69d084561156234c96fff80515`,
[run 42161227944](https://github.com/patchwerks/furbomek/actions/runs/42161227944)
attempt 1, timed out on Node 26 / Chromium while waiting for the native chooser
after Space. The chooser event was not observed; file selection and parsing
were not reached. Pre-action evidence showed the input focused and visibly
outlined, within the viewport, with the document focused. That does not prove
keyboard delivery, activation, focus at keyup or chooser interception.

The unchanged job passed its retry, and the later docs-only `f662` head passed
its matrix on the first attempt. Other browser/Node jobs passed. The cause remains
unresolved; these results do not establish a repair or Node-specific cause.
The next candidate adds passive diagnostics around the genuine keyboard path,
retaining one real Space-to-chooser interaction and the existing timeout.
Diagnostics are evidence collection, not a claimed fix. Do not substitute upload
injection, clicks, forced focus, retries, sleeps or longer timeouts for native
keyboard acceptance. Any future failure remains a failure and requires analysis
of event delivery, activation, interception and frame state before proposing a fix.

## Rollback and ownership

Root coordination owns the claim, source freeze, hosted qualification and
publication. Before acceptance, revise or discard only this candidate's changes.
After acceptance, a separately authorized reviewed revert of its accepted commit
can restore prior behavior. No host configuration or live deployment changed,
so this slice has no host rollback action.

## First hosted attempt and focused correction, 2026-11-06

**Observed:** [viewer run 42186596389](https://github.com/patchwerks/furbomek/actions/runs/42186596389)
failed both Node jobs at normal typechecking. Both retained `types.log` files
report TS2345 at `PackBuilder.vue(38,12)`: the indexed cue lookup can be
`undefined` under `noUncheckedIndexedAccess`. This run did not reach the unit
or browser checks and does not qualify the new behavior.

The focused correction checks that the captured reactive cue exists before
focusing it after `nextTick`. It retains the same stable cue identity and adds
no type assertion, suppression, test change or workflow change. Static diff
inspection is complete; execution of the corrected revision remains pending.
The failed attempt is retained as evidence and is not replaced by a retry claim.

## Exact-source qualification and diagnostic correction, 2026-11-06

The first failed source was `0e2ceb39ef9c102d737713fde45907dbc877d67f`.
After the guarded focus correction, source
`c91435a7a2179465d93933b6f9ddc9ada7d72a56` passed all 12 checks, including
[viewer run 42187130957](https://github.com/patchwerks/furbomek/actions/runs/42187130957)
and [metadata run 42187131114](https://github.com/patchwerks/furbomek/actions/runs/42187131114).
The viewer passed 66 unit cases per Node job and 54 browser cases in each of
four browser/Node combinations; metadata passed 90 combined tests per Node job
with no skips. This established bounded behavior, but its event diagnostics
overwrote event `type` with the input's type, leaving event names incomplete.

The next source, `4e2baf1439d67e9470f037ea0e5a7b9702b6b9d6`, names the
control field `inputType` and asserts trusted Space keydown/keyup, one chooser
and completed key press. This changes test diagnostics and assertions, not
production UI bytes. Its [viewer run 42187842791](https://github.com/patchwerks/furbomek/actions/runs/42187842791)
passed attempt 1 on both jobs:

| Worker | Targeted lint | Unit cases | Chromium 156.0.8078.4 | Firefox 157.0 |
| --- | --- | --- | --- | --- |
| Node 22.22.3 | 16 files; 0 errors/warnings | 66 passed | 54 passed | 54 passed |
| Node 26.7.0 | 16 files; 0 errors/warnings | 66 passed | 54 passed | 54 passed |

Both jobs passed normal typechecking, the injected negative control,
restored-source typechecking and static generation. All 43 existing browser
cases remain in the 54-case inventory. The four diagnostic traces now retain
`keydown`, `keypress`, `keyup` and `click` event names, trusted Space down/up
targeting the input, `inputType=file`, exactly one chooser and a completed press,
with no diagnostic error. These observations do not resolve the historical
intermittent timeout. Instrumentation can change timing; successful instrumented
runs are not proof that instrumentation repaired the cause.

All four browser records have empty CSP-violation, outbound-request and page-error
arrays, and zero console errors. Console warnings remain: one Chromium warning
and seven Firefox warnings per run. Retained messages concern unsupported
`WEBGL_lose_context`, destination-rectangle size during `drawElementsInstanced`,
debug-renderer-info deprecation and intentional context loss. This is not a
console-clean claim or a claim that every warning's cause is fully diagnosed.

The exact-source [metadata run 42187842684](https://github.com/patchwerks/furbomek/actions/runs/42187842684)
passed 90 combined tests per Node job: 59 core plus 31 metadata, with zero
failures, skips, cancellations or todos. The actual unreadable-file permission
case passed in both workers. [Non-live verification 42187842786](https://github.com/patchwerks/furbomek/actions/runs/42187842786)
and [CodeQL 42187837510](https://github.com/patchwerks/furbomek/actions/runs/42187837510)
also passed; all 12 source checks succeeded.

## Artifact provenance and visual review, 2026-11-06

| Artifact | GitHub ID | Verified downloaded ZIP SHA-256 |
| --- | --- | --- |
| Node 22 viewer qualification | 13488332935 | `16b34c54f0e124c717123319e6c9a0bee745ba9858676766ec3e78dc15ce3ae4` |
| Node 26 viewer qualification | 13488491788 | `f716e2ec0d334435236cd0e0f4b50bfc0fd1b630b5c06f8cf1f9534f56188c7a` |

Downloaded archive hashes match GitHub artifact metadata. Embedded source records
identify `4e2baf1439d67e9470f037ea0e5a7b9702b6b9d6`; the enforcement pin is
`cdd9147fac9141fa0c75b5058f9dce46c7885188`. Artifact names contain the workflow
merge-context SHA `64d3313ee86c25885a9557d14564c82a8c8c68b3`, not the source
identity. Verification used the explicit embedded source and provider metadata.
Inert archive inspection checked unique allowlisted regular entries, no more than
40 entries, at most 8 MiB per file and 32 MiB per job before extraction. No
artifact was executed on the credentialed host.

Coordinator independently inspected the earlier `c91435a7` artifacts and actual
Node 22 Chromium builder-light, Node 26 Firefox builder-dark and Node 22 Firefox
builder-mobile screenshots. Native arrows, focus and layout were readable, with
no correction required. Production UI bytes are identical at `4e2baf14`.
Coordinator also independently verified the latest ZIP hashes, embedded source
and all four 54-case records, and inspected the latest Node 26 Firefox
builder-error screenshot: readable validation error, disabled export/transport
and a neutral proxy, with no visual correction required.

These source results supersede the earlier execution-pending preparation
checkpoint, while preserving the initial failure and diagnostic correction.
The documentation-bearing head still requires its own checks and independent
review; root will bind that completion in the PR/issue record. No merge,
deployment, full accessibility, actual browser-zoom, screen-reader or physical
qualification is claimed.

## Changelog

- 2026-11-06: Recorded verified `4e2baf14` source qualification and artifact
  digests; preserved the earlier type failure, `c91435a7` diagnostic limitation,
  WebGL warnings and unresolved picker cause. Final documentation-head checks
  and independent review remain pending.

- 2026-11-06: Recorded first hosted normal-typecheck failure and guarded the
  indexed cue before focusing; corrected-revision execution remains pending.

- 2026-11-06: Prepared bounded keyboard, native-select, announcement-semantics and
  CLI diagnostics follow-up; retained unresolved native-picker history and
  pending exact-source execution/acceptance.
