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

**Pending in the existing disposable offline CI matrix:** root Nuxt preparation
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
pending. Do not describe this candidate as runtime-proven or close issue 32.

## Rollback

Revert this bounded viewer/qualification addition to return to the accepted
preview-only viewer. Exported files remain ordinary presentation pack v1 JSON;
no migration or runtime deployment is involved.

## Changelog

- 2026-11-05: Prepared browser authoring and combined offline download/metadata
  checks; execution and visual review remain pending.
