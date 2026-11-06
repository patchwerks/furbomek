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
