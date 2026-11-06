---
created: 2026-11-05T08:13:11Z
branch: codex/32-pack-metadata
author: patchWERKS / Codex
status: active
---
# Companion presentation metadata

This candidate adds a separate companion JSON file for a presentation pack.
The [presentation pack v1 format](presentation-packs.md) and its core parser are
unchanged. Metadata is optional; validation reports `absent` or `matched`.
Neither outcome grants installation, execution, authorship verification, media
rights, security approval, or live robot authority.

The exact flat fields are:

| Field | Required value |
| --- | --- |
| `metadataVersion` | Integer `1` |
| `packId` | The validated pack's ID |
| `packVersion` | The validated pack's version |
| `previewContractVersion` | Integer `1`, matching the pack |
| `author` | Explicit public name, 1–80 Unicode code points; no surrounding whitespace, Unicode control/format/surrogate/unassigned/private-use characters or line/paragraph separators |
| `license` | Explicit `MIT` or `CC0-1.0`; no default |
| `packSha256` | 64 lowercase hex digits: SHA-256 of the exact pack bytes |

The license is a self-declared claim about the data-only pack. The tool cannot
verify ownership or authority to license it. It supplies no media grant. The
name is public metadata, not an authenticated identity. No asset, URL, path,
executable field, nested value or unknown key is accepted.

Metadata is strict UTF-8 JSON without a BOM, at most 16 KiB. Duplicate keys are
rejected after JSON escape decoding. Missing fields, wrong types, unsupported
versions, incompatibility and digest mismatches fail closed. Reformatting a pack
changes its digest even when the parsed timeline is identical; create a new
companion after changing any bytes.

## Candidate command interface

Run candidate code only in a reviewed, credential-free disposable offline
worker. At source `1a0e5ae66e4ffe28c7cdc2c03860cae2f97ced38`, the metadata/core
suite passed all 87 tests on Node 22.22.3 and 26.7.0 in
[run 41994352925](https://github.com/patchwerks/furbomek/actions/runs/41994352925).
See the [qualified-source record and limits](../operations/presentation-metadata-2026-11-05.md).
The real browser-download/CLI roundtrip and byte-tamper rejection also passed
in all four Chromium/Firefox build combinations at that source; see the
[builder record](../operations/pack-builder-2026-11-05.md). Final-head checks and
independent acceptance remain separate gates; evidence applies only to that source.
From the repository root:

```sh
node tools/presentation-pack/cli.mjs validate /explicit/pack.json
node tools/presentation-pack/cli.mjs validate /explicit/pack.json --metadata /explicit/companion.json --json
node tools/presentation-pack/cli.mjs template /explicit/pack.json --author 'Public Author' --license MIT
```

`template` emits only companion JSON to stdout and creates no file. The caller
chooses whether and where to save it. `validate --json` emits one result object
to stdout, including `ok`, and `metadata: "absent"` or `"matched"` on success.
Invalid/file results carry `error: "invalid"`; usage results carry `error:
"usage"`. Exit status is 0 for success, 1 for invalid input/file failure and 2
for usage errors. Non-JSON errors use stderr. JSON output and plain diagnostics
escape controls and non-ASCII characters, including filename bidi controls.
Use `./` before a filename beginning with `--`; flags and values may not repeat.

Only the supplied paths are read. There is no auto-discovery, globbing,
directory walking, networking, archive extraction, installation or output-file
write. The CLI reads each input through one bounded regular-file descriptor
with `O_NOFOLLOW` and `O_NONBLOCK`, verifies identity and change metadata before
and after the read, and closes it on failure. Unsupported flags fail closed.
The pack parser and SHA-256 receive the same byte buffer from that single read.

The final component cannot be a symlink. Parent directories must be trusted;
this is not an `openat` directory capability sandbox and does not prevent
symlink traversal in parents. Checks detect ordinary concurrent changes, not a
transactional snapshot against a privileged adversary or an untrustworthy
filesystem. The result describes the bytes read, not future contents at the
same path. Run against trusted, stable local input storage.

## Verification scope

The candidate advisory workflow uses pinned Node 22.22.3 and 26.7.0 containers,
no dependencies, only read-only mounts of the tools and unchanged core package,
and a writable temporary filesystem for test fixtures. It runs strict-format,
file-boundary/race, same-byte hash, CLI and existing core tests. It is not an
independent policy acceptance mechanism. Combined builder checks must also
validate an actual browser download through this CLI, generate and match its
companion in temporary storage, and reject a byte-tampered pair.


## Changelog

- 2026-11-05: Replaced preparation-only runtime status with observed Node 22/26
  metadata/core source qualification; retained combined integration, final-head
  and independent acceptance gates.

## Browser byte validation candidate (2026-11-06)

`tools/presentation-pack/browser.mjs` exports
`validateBrowserMetadata(packBytes, metadataBytes)`. Both arguments must be
`Uint8Array` views, bounded to 1 MiB and 16 KiB respectively. The returned promise
resolves to a frozen `{ pack, metadata, packSha256 }`: the original branded,
deeply frozen core parse result, the frozen strict companion, and a lowercase
SHA-256 digest of the exact supplied pack bytes. The declaration in
`browser.d.mts` retains the core `ParsedPack` type.

The function checks sizes before allocation and synchronously copies both byte
views before its first await. Parsing, hashing and matching use these snapshots;
ordinary caller mutation after invocation cannot change the result. Offset views
include only their visible bytes. SharedArrayBuffer-backed inputs are rejected;
this is not a boundary against arbitrary hostile JavaScript in the same context.
There is no caller-supplied parsed-object or digest shortcut.

Native Web Crypto SHA-256 requires a secure browser context (HTTPS or a browser's
trusted loopback context). Missing or rejecting Web Crypto produces the fixed
error `Browser metadata validation requires Web Crypto SHA-256 in a secure
context`; there is no fallback hash implementation. Digest semantics follow the
[Web Crypto recommendation](https://www.w3.org/TR/2017/REC-WebCryptoAPI-20170126/#SubtleCrypto-method-digest).
The module does not read files, store data, request URLs, install packs or wire
viewer UI. Its result verifies byte/format compatibility only; names and licenses
remain unverified self-declarations. Appending whitespace to the pack requires a
new companion even if its parsed content is unchanged.

Candidate tests cover the wrapper trust boundary with native Node Web Crypto and
isolated module contexts. A separate fixed-route loopback browser harness imports
the actual three browser modules and exercises native Web Crypto in Chromium and
Firefox. Its ten cases and `browser-metadata-results.json` are separate from the
existing viewer's 43 cases and evidence. Hosted execution and independent review
remain pending; see the [candidate record](../operations/browser-metadata-2026-11-06.md).
