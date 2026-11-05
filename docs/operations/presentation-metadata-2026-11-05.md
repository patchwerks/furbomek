---
created: 2026-11-05T08:13:11Z
branch: codex/32-pack-metadata
author: patchWERKS / Codex
status: active
---
# Presentation metadata preparation

**Implemented candidate; runtime qualification pending.** Linked work is
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
