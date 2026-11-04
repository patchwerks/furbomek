---
created: 2026-11-01T22:05:19Z
branch: codex/32-extension-contract
author: patchWERKS / Codex
status: active
---
# Data-only extension preview core

Accepted first slice for [issue 32](https://github.com/patchwerks/furbomek/issues/32):
[PR 41](https://github.com/patchwerks/furbomek/pull/41) merged on 2026-11-04 at
`ccad3d5c9cd9d52c83af20e21163dbd4b0ea8463` from reviewed head
`8c38c3fd814cc7dfdfd25ee706e5718f28f0de28`.
This private, dependency-free ESM package parses a bounded JSON presentation pack
and samples its timeline. A future viewer may consume the samples. This slice
selects no UI, renderer, character asset, 3D model, or asset license. Nothing is
connected to the live character broker, Hermes, jabberWERK, OBS, or robot.

## API

- `parsePack(bytes: Uint8Array)` from `index.mjs` returns a deeply frozen pack.
  Invalid input throws `TypeError`. Byte input is required; there is no arbitrary
  object validation API that could execute getters supplied by a pack.
- `samplePack(pack, positionMs)` from `index.mjs` accepts only exact objects
  returned by this module's `parsePack`. Clones, forged objects and objects parsed
  by a separate module instance are rejected before property access. It returns
  a fresh frozen `{ positionMs, expression, reaction, reactionProgress }` sample.
- `await loadPackFile(path)` from the separate Node-only `load-file.mjs` entry
  reads an explicit operator-selected regular file. The browser entry does not
  import this loader. No package installation is needed for direct ESM use.

The core has no Node imports, filesystem, network, timers, dynamic code execution,
or renderer dependencies. `fixtures/reaction.json` is a synthetic contract
example, never a substitute for observed live character state.

`index.d.mts` provides type-only descriptions of the browser API, reviewed against
its JavaScript implementation. The private nominal brand describes validated
parser results for TypeScript consumers; the runtime WeakSet remains the authority.
These declarations do not typecheck the core JavaScript internals.

## Contract v1

Root fields are exactly `schemaVersion`, `packId`, `packVersion`,
`previewContractVersion`, `capabilities`, `durationMs`, `events`. Both contract
versions are `1`; the package version is independently `0.1.0`.
`packId` matches `^[a-z][a-z0-9-]{0,63}$` across the entire string
(with an additional strict end assertion, so a trailing newline is rejected). `packVersion` has three numeric SemVer
components, no leading zeroes except zero itself, no prerelease/build suffix,
and at most 32 characters; it also requires the strict end of the string. No field carries paths, URIs, code or asset references.

Capabilities are a unique list of one or two entries:
`presentation.expression` (required) and optional `presentation.reaction`.
They are presentation template capabilities, never physical actions or permission
grants. Expressions are `neutral` or `curious`; the sole reaction is `acknowledge`.

Duration is an integer from 1 to 30,000 ms. There are 1–64 events with exactly
`seq`, `atMs`, `kind`, `value`. Sequences are contiguous from 1, timestamps are
nondecreasing integers in `[0, durationMs)`, and each kind must be declared.
Event 1 is a neutral expression at zero. Every event at zero must also be a
neutral expression, guaranteeing neutral reset. Equal-time events apply in
sequence order, with the latest event of each kind winning.

Input is at most 1 MiB before decoding. Only fatal-decoded UTF-8 without BOM is
accepted. JSON keys must be unique after escape decoding at every level; nesting
is limited to eight containers including the root. Numbers must be finite JSON
numbers. Unknown or missing fields at any level fail closed. Archives are invalid
JSON input; nothing is extracted. `pack.schema.json` describes structural rules;
its comment identifies semantic and byte-level rules enforced by `parsePack`.

## Deterministic sampling

The caller supplies finite nonnegative elapsed milliseconds, including fractions.
No clock, wall time, previous sample, frame delta or accumulated state participates.
Seeking backward and resetting to zero therefore have the same result as sampling
those positions for the first time. The most recent expression event applies:
`curious` expires after 1,000 ms, while `neutral` immediately clears it. The most
recent reaction expires after 600 ms; while active its progress is
`(positionMs - atMs) / 600` in `[0, 1)`. Inactive reaction is `null` with progress 0.
At or beyond duration, time clamps to duration and both channels are neutral/clear.
The timeline never loops implicitly.

## File boundary and verification limits

The Node loader rejects final-component symlinks and nonregular files, requires
`O_NOFOLLOW` (fails closed on unsupported platforms), checks inode/device after
open, reads at most 1 MiB + 1 byte into a fixed allocation, and checks descriptor
size and modification/change times before/after reading. `O_NONBLOCK` avoids a
raced FIFO blocking open where supported. The operator owns the parent directory
and explicit path; this is not a sandbox against hostile parent-directory mounts
or an atomic snapshot guarantee against a privileged writer. Linux is the first
qualification target; Node 22 and 26 use the same direct ESM entries.

Candidate runtime tests belong in a credential-free disposable environment. See
the [dated implementation record](../../docs/operations/extension-preview-2026-11-02.md)
for the original implementation evidence and its recorded limits. This package has
no install, activation, deployment or live-operation command.

## Contributor starter kit

The [presentation-pack authoring guide](../../docs/contributing/presentation-packs.md)
provides three original JSON examples, timing expectations and dependency-free
checks against the accepted PR 41 contract. Contributor checks live in
`docs/contributing/tests/presentation-packs.test.mjs`; the guide gives separate
starter and combined-suite commands. Package-only tests need no contributor docs. This kit remains an unapproved draft
under issue 32 requiring its own independent review. The optional PR 42 viewer
is a separate unapproved draft absent from this kit. The guide does not define a
stable external API or grant live authority.

## Changelog

- 2026-11-04: Documented the type-only browser API declarations and retained the
  runtime parser-brand authority and JavaScript verification boundary.

- 2026-11-04: Recorded core acceptance through PR 41; contributor kit and viewer
  still require separate acceptance.

- 2026-11-02: Linked the draft contributor kit with neutral, curious and acknowledge
  examples; preserved the core contract and separate viewer review boundary.
