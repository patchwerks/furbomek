---
created: 2026-11-05T08:13:13Z
branch: codex/32-pack-builder
author: patchWERKS / Codex
status: active
---
# Local browser pack authoring preparation

Canonical task: [issue 32](https://github.com/patchwerks/furbomek/issues/32).
Base: `c0c3f7ce44cfa3db34cbe46a723bf1fc16b56b6c`. This record describes
candidate source, not acceptance or installed/live behavior.

## Implemented source

The existing standalone Nuxt/Vue/Bootstrap viewer gains an explicit Build mode.
Entry copies the current parsed pack into an editable draft; neutral, curious
and acknowledge presets start new drafts with the accepted examples’ timings
(1200 ms neutral; 2000 ms curious with a 400 ms cue; 1600 ms acknowledge
with a 300 ms cue). Restore loaded pack returns to the
entry snapshot. ID, version, duration and cue values/times are editable; the
first neutral cue at zero is locked. Add/remove is bounded to 64 total cues.
Serialization orders times stably, regenerates contiguous sequence values,
derives capabilities and validates the exact UTF-8 export bytes through the
unchanged shared parser. Export uses a local Blob, a parser-constrained
`packId.json` filename and revoked object URLs.

Every edit pauses and resets the preview. Invalid drafts clear the parsed pack,
events and identity, display validation errors and disable export/playback.
Entering Build supersedes pending imports. The existing context-loss, reduced
motion, visibility and teardown paths remain in the parent viewer. The builder
has no Node CLI import, persistence, network, media, asset or live authority.

## Design audit and decisions

**Source-inspected:** the existing workbench uses system typography, restrained
Bootstrap controls, shared surface/ink/muted/accent/error tokens, visible focus
outlines and a single-column mobile breakpoint. Preserve those choices with
DESIGN_VARIANCE 3, MOTION_INTENSITY 2 and VISUAL_DENSITY 5. New controls use real
labels, native keyboard behavior, readable inline guidance and an alert region.
Inputs/selects use the same light/dark surface tokens, including focused and
locked states. Cue rows stay within the narrow inspector. No imagery was selected
or generated; the original procedural proxy is unchanged.

## Qualification and evidence limits

**Observed on the preparation host:** JavaScript syntax-only checks for the new
helper/tests and updated browser runner, plus whitespace checks. These checks do
not execute candidate modules and are not runtime, type, accessibility or visual
qualification. No dependency installation, build, browser or test suite was run
on the credentialed host.

**Initial preparation checkpoint (superseded by the source results below):** root Nuxt preparation
and targeted ESLint on viewer and presentation-pack tools with zero warnings;
unchanged normal strict
typechecking, exact negative-control diagnostic and restored typecheck; static
generation; all existing core/artifact tests plus builder helper cases; all
existing Chromium/Firefox browser cases plus builder cases on Node 22/26 jobs.
The browser runner now exercises actual download and reimport, presets, restore,
locked reset, stable ordering, invalid-state clearing, edit pause/reset, 64-cue
limit/removal, object-URL revocation and keyboard/mobile behavior.

The combined browser test invokes the separately prepared
`tools/presentation-pack/cli.mjs` on the real downloaded bytes in temporary worker
storage: validate, emit a test-author/MIT companion template, validate the pair,
then append JSON whitespace and require the old digest to fail. This test must
run after both workstreams are integrated; it does not substitute for the tool's
own strict-parser and file-boundary tests.

The existing workflow trust pins, credential-free worker boundaries and negative
control are retained. Its declaration exception adds only `builder.d.mts`; its
bounded evidence allowlist adds `root-prepare.log`, `authoring-lint.json`,
`builder-light.png`, `builder-dark.png`,
`builder-mobile.png` and `builder-error.png`. The tools path triggers this combined
regression workflow. Real screenshot inspection, execution results, immutable
source/artifact provenance, final-head checks and independent acceptance remain
pending at preparation. The results below qualify only their exact source;
independent acceptance remains separate and issue 32 stays open.

## Exact-source isolated qualification, 2026-11-05

**Observed:** combined source `1a0e5ae66e4ffe28c7cdc2c03860cae2f97ced38`
passed [viewer run 41994353036](https://github.com/patchwerks/furbomek/actions/runs/41994353036)
(attempt 1, PR 48). Both downloaded `candidate-sha.txt` records match that source;
the enforcement pin is `cdd9147fac9141fa0c75b5058f9dce46c7885188`.
Artifact names contain workflow merge-context SHA
`16d17e14ceb6e7a6886914cb05295f7e24f41f8f`; the source identity comes from the
explicit checkout, artifact content and GitHub run/artifact metadata, not its name.

| Worker | npm | Targeted lint | Core/artifact/helper tests | Browser cases |
| --- | --- | --- | --- | --- |
| Node 22.22.3 | 10.9.8 | 16 files, 0 errors, 0 warnings | 66 passed; 0 failed/skipped | Chromium 43; Firefox 43 |
| Node 26.7.0 | 11.19.0 | 16 files, 0 errors, 0 warnings | 66 passed; 0 failed/skipped | Chromium 43; Firefox 43 |

Both workers passed root/viewer preparation, normal strict typechecking, the
injected `app.vue(35,34)` TS2339 negative control, restored-source typechecking
and static generation. Chromium 156.0.8078.4 used SwiftShader; Firefox 157.0 used
Xvfb/Mesa llvmpipe. All four browser records contain empty outbound/error arrays.
The 43 cases comprise all 31 previous cases plus 12 builder cases. The latter
include real Blob download, UI reimport, downloaded-byte CLI validation/template/
companion verification, exact-byte whitespace tamper rejection, URL revocation,
presets, restore, locked reset, pause/reset, invalid-state clearing, cue limits
and keyboard/mobile behavior. The companion tool's separate qualification remains
recorded in its [operations record](presentation-metadata-2026-11-05.md).

The first combined viewer attempt stopped at targeted lint: two
`no-control-regex` findings in metadata test assertions (lines 117 and 121),
confirmed in both first-attempt lint JSON files. This was a test-source lint
failure, not a browser/product failure. The corrected exact source above passed
without suppressing rules or weakening the lint gate.

| Artifact | GitHub ID | Downloaded ZIP SHA-256 |
| --- | --- | --- |
| Node 22 viewer qualification | 13400230319 | `3975b4a65cea271d702b9d1783f549397ad1dbee497db2f4a24944fedcb3407c` |
| Node 26 viewer qualification | 13399233211 | `284fe874fe91da5211c73bfa9f12acb381b9b155dc52d67ce1227f6d97fd03d0` |

Both archive digests matched GitHub metadata. Before extraction, inert inspection
checked source identity, non-expiry, exact path allowlists, unique names, regular
files/directories without symlinks, per-file size, total expansion and member count.
Only allowed logs/JSON/text and PNG screenshots were extracted; no artifact was
executed on the credentialed host. Each browser/job supplies builder light, dark,
mobile and invalid-draft screenshots alongside the existing preview screenshots.
Coordinator inspected Node 22 Chromium builder light/mobile, Node 26 Firefox
builder dark/invalid-draft and default-preview light PNGs. Forms and focus rings
are legible, narrow controls wrap without visible clipping, and invalid-state
copy/disabled export are visible. The established workbench/proxy presentation
is retained; no visual correction was required.
These bounded Linux browser checks do not establish full accessibility or arbitrary
browser compatibility. Final documentation-head checks and independent PR 48
acceptance remain required; issue 32 stays open.

## Rollback

Revert this bounded viewer/qualification addition to return to the accepted
preview-only viewer. Exported files remain ordinary presentation pack v1 JSON;
no migration or runtime deployment is involved.

## Changelog

- 2026-11-05: Recorded exact-source isolated matrix, actual downloaded artifacts
  and combined browser/CLI proof; retained visual, final-head and acceptance gates.

- 2026-11-05: Prepared browser authoring and combined offline download/metadata
  checks; execution and visual review remain pending.
