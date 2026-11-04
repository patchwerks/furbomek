---
created: 2026-11-02T09:29:19Z
branch: codex/32-contributor-kit
author: patchWERKS / Codex
status: active
---
# Author a presentation pack

**Draft contributor kit for [issue 32](https://github.com/patchwerks/furbomek/issues/32).**
The core contract in [PR 41](https://github.com/patchwerks/furbomek/pull/41)
was accepted and merged on 2026-11-04 at
`ccad3d5c9cd9d52c83af20e21163dbd4b0ea8463`, from reviewed head
`8c38c3fd814cc7dfdfd25ee706e5718f28f0de28`. This contributor kit remains
unapproved and does not establish a stable external API. The optional viewer is a separate draft in
[PR 42](https://github.com/patchwerks/furbomek/pull/42); it is not included in this
kit. This kit and the viewer require their own independent review.

A pack is a small UTF-8 JSON timeline. It describes neutral or curious expression
and an acknowledge reaction for an offline presentation preview. It contains no
executable code, images, audio, gait, model files or asset references. It cannot
install anything or grant live broker, Hermes, OBS, voice or robot authority.

## Start with a complete example

Choose a file from [the examples directory](../../packages/extension-preview/examples/):

| File | What it teaches | Expected samples in milliseconds |
| --- | --- | --- |
| [neutral.json](../../packages/extension-preview/examples/neutral.json) | Smallest useful reset baseline | At 0 and 1199: neutral. At 1200 and later: neutral, with position clamped to 1200. |
| [curious.json](../../packages/extension-preview/examples/curious.json) | One expression with automatic expiry | At 399: neutral. At 400 and 1399: curious. At 1400: neutral. At 2000 and later: neutral. |
| [acknowledge.json](../../packages/extension-preview/examples/acknowledge.json) | One reaction over a neutral expression | At 299: no reaction. At 300: acknowledge, progress 0. At 600: acknowledge, progress 0.5. At 900: no reaction, progress 0. At 1600 and later: neutral and clear. |

Neutral and curious examples always have `reaction: null` and
`reactionProgress: 0`. The acknowledge example always has `expression: "neutral"`.
These are synthetic authored examples, not observations of the live character.
The existing [combined fixture](../../packages/extension-preview/fixtures/reaction.json)
shows both channels together.

This is the complete neutral example, ready to save as UTF-8 without a BOM:

```json
{
  "schemaVersion": 1,
  "packId": "starter-neutral",
  "packVersion": "0.1.0",
  "previewContractVersion": 1,
  "capabilities": ["presentation.expression"],
  "durationMs": 1200,
  "events": [
    { "seq": 1, "atMs": 0, "kind": "presentation.expression", "value": "neutral" }
  ]
}
```

1. Copy the closest example to a file you own. Choose a distinct `packId` and keep
   the initial neutral event intact.
2. Keep both contract version fields at `1`. Use `packVersion` for your own pack's
   revision, starting at `"0.1.0"`; it is independent of the contract versions and
   of the preview package's software version.
3. Edit event values and times within the rules below. Add
   `presentation.reaction` to capabilities before adding acknowledge events.
4. Check the file, then inspect samples just before each cue’s start (at a
   nonnegative time), at its start, just before expiry, at expiry and at the end.
   Sample time must never be negative. Check backward seeks and reset to zero.
5. Submit the JSON with a short description of intended timing, provenance and
   actual verification results. Follow the repository's
   [contribution coordination](../agents/coordination.md) and
   [issue workflow](../agents/issue-tracker.md).

## Field and timing rules

The root has exactly these seven fields; no extra metadata fields are supported.

| Field | Required value or range |
| --- | --- |
| `schemaVersion` | Integer `1`. |
| `packId` | 1–64 characters: starts with lowercase ASCII letter; remaining characters are lowercase ASCII letters, digits or hyphens. No trailing newline. |
| `packVersion` | Three numeric components, such as `"0.1.0"`, at most 32 characters. No leading zeroes except zero itself, prerelease label, build suffix or trailing newline. |
| `previewContractVersion` | Integer `1`. |
| `capabilities` | Unique list of one or two entries. `presentation.expression` is always required, even for a pack focused on reactions; `presentation.reaction` is optional. |
| `durationMs` | Integer from 1 through 30,000. |
| `events` | 1–64 events, each with exactly `seq`, `atMs`, `kind` and `value`. |

`seq` starts at 1 and increases by exactly one in array order. `atMs` is an
integer at least zero and strictly less than `durationMs`; times never decrease.
Every event kind must appear in capabilities. The kind
`presentation.expression` accepts only `neutral` or `curious`;
`presentation.reaction` accepts only `acknowledge`.

Event 1 must be a neutral expression at 0. **Every event at 0 must also be a neutral
expression**, including tied events. At later tied times, sequence order applies:
the last event of each kind wins. The expression and reaction channels are separate.

Curious lasts for 1,000 ms from its event, unless a newer expression replaces it.
A neutral event immediately clears curious. Acknowledge lasts for 600 ms, unless a
newer reaction replaces it. Active reaction progress is elapsed time since that
event divided by 600, from 0 inclusive to 1 exclusive. At exactly expiry, reaction
is `null` and progress is 0. Neither state continues forever, and there is no
implicit loop. Duration can cut either channel short: at or beyond the end,
expression is neutral, reaction is `null`, progress is 0 and position clamps to duration.

Sampling is stateless. `samplePack(pack, positionMs)` takes a finite nonnegative
number of elapsed milliseconds; fractional sample positions are allowed even
though event times are integers. Sampling 900, then 300, then 0 is equivalent to
sampling each position independently. There is no internal clock or accumulated
frame delta. Use the exact immutable result of `parsePack(bytes)` (or
`loadPackFile(path)`); a cloned or independently reconstructed object is rejected.
See the [core API](../../packages/extension-preview/README.md) and
[schema](../../packages/extension-preview/pack.schema.json). JSON Schema alone does
not enforce all parser rules.

## Check your pack without installing dependencies

Run candidate code only in a disposable, credential-free offline worker with no
production network or device access. From the repository root, with Node 22 or 26
available, the dependency-free starter check is:

<!-- starter-check -->
```sh
node --test packages/extension-preview/tests/starter-examples.test.mjs
```

That checks the committed examples and the complete JSON blocks in this guide.
To validate a file you have edited, use the existing Node file loader. The final
quoted argument is the explicit file path; replace it with your own regular JSON
file inside a directory you control. This command succeeds with
`Valid pack: starter-neutral` for the supplied example and fails on rejected input.

<!-- starter-validate-file -->
```sh
node --input-type=module -e 'import { loadPackFile } from "./packages/extension-preview/load-file.mjs"; const pack = await loadPackFile(process.argv[1]); console.log(`Valid pack: ${pack.packId}`);' -- 'packages/extension-preview/examples/neutral.json'
```

Optional full package suite:

<!-- starter-full-suite -->
```sh
node --experimental-vm-modules --test packages/extension-preview/tests/*.test.mjs
```

No `npm install`, `npm ci` or `npx` is needed. In particular, the root package's
postinstall performs unrelated build and dependency work. A passing local check
is evidence for that checked revision, not acceptance, deployment or authorization
for live operation.

The loader accepts an explicitly selected regular file, rejects final-component
symlinks and requires platform support for `O_NOFOLLOW`. It bounds reads and
checks file identity and changes during the read. The parent directory must be
trusted; this is not a sandbox against hostile parent mounts or a privileged
writer. Input is limited to 1 MiB of strict UTF-8 JSON without BOM. It performs
no archive extraction. See [file boundary limits](../../packages/extension-preview/README.md#file-boundary-and-verification-limits).

## Optional draft viewer

The separate [pinned PR 42 source at 92b7c146](https://github.com/patchwerks/furbomek/tree/92b7c14699d125177bd3f01d896b25ebe3ffa02b)
contains the draft viewer; follow that revision's instructions in its own isolated
review environment. If a reviewer has already opened that viewer, use **Import
local JSON** to select your file, then inspect the timeline and sample boundaries
above. This kit supplies neither viewer files nor a deployed viewer URL. Viewer
preview is an optional inspection aid and does not replace the parser check or
independent review.

## Common rejections and review checklist

Common rejected inputs include a curious or reaction event at time zero; an event
at exactly duration; a missing, duplicate or skipped sequence; decreasing times;
an undeclared capability; an unknown field, value or capability; and a reaction
pack that omits the required expression capability. JSON comments, trailing commas,
duplicate keys (including escape-equivalent keys), a BOM, malformed UTF-8,
non-finite numbers and more than eight nested containers also fail. A file can
pass a generic JSON parser or schema checker and still fail this contract.

Before requesting review:

- Confirm the ID, pack version, capabilities, contiguous sequence and neutral reset.
- Record the intended samples at start, expiry and end, including backward seek.
- Run the starter check and validate the actual submitted file; record Node version,
  source revision, command and result. Do not report a planned run as passing.
- Keep provenance in the contribution description or companion documentation,
  because arbitrary metadata is not part of the pack schema.
- Include only original JSON event data you can contribute. These three starter
  examples were authored for this kit and contain no third-party source assets.
  They grant no rights to imagery, voices, models or other media.
- Keep audio, gait, asset loading, installation, broker writes and live authority
  outside the pack. The contract has no fields or runtime for them.

## Changelog

- 2026-11-04: Recorded accepted PR 41; kept contributor-kit and viewer acceptance
  separate and pending.

- 2026-11-02: Added the draft authoring guide and three original data-only examples
  for issue 32; core and viewer acceptance remain separate review gates.
