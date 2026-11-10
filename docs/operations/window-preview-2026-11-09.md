---
created: 2026-11-10T06:40:00Z
branch: work/55-window-preview
author: Hephaestus
sprint: WP-55
status: active
---

# Window-only Hermes preview: WP-55

Canonical work and acceptance: [issue 55](https://github.com/patchwerks/furbomek/issues/55).
This bounded work package was added after discovering the newly adopted Agentile
entrypoint in published main. The original discovery used the older checkout's
guidance; implementation and release require independent re-review of the entire
delta against the pinned policy, not grandfathering that discovery gap.

## Approved boundary

The user explicitly approved selected browser/application windows, not whole
desktops. Capturing a named XComposite window hierarchy excludes sibling windows,
the desktop, window-manager decorations and separate top-level dialogs. Child
windows belonging to the selected hierarchy are included. Transparent pixels are
composited onto fixed RGB32, never the visible underlay. This does not detect or
redact secrets displayed inside the selected application. Shutter before entering
private content; an agent cannot claim an asynchronous observer certifies pixels.
Hooks remain read-only and neither grant nor revoke the window capability.

The gate assumes cooperative processes under the current Unix UID. It is not a
sandbox against hostile same-UID X11 clients or a credential isolation boundary.
There is no full-desktop fallback, implicit active-window following or title-based
retargeting. Off remains the default; legacy `bot-desktop` remains rejected.

## Agent operation

Read root, activity, supervisor and Kinect tool guides. Own the media resource
window before starting anything. Preserve unrelated desktops/chats and robot tools.
Use an explicitly chosen profile's dedicated Hermes desktop, not the operator's
seat. Installed Hermes v0.22.5 at `bf0203a794a0` was consulted along with its
`website/docs/user-guide/features/bot-screen.md` and browser documentation.

Start the chosen desktop through Hermes's supported API/CLI only. Use `umask 077`
when provisioning runtime state; the installed launcher otherwise creates its PID
record with the caller's umask, and this module rejects a permissive PID record.
Validate DISPLAY, profile-local Xauthority and launcher birth; never print cookies.

From the activity module, build `native/build-x11-window-capture.sh` into
`PROFILE_HOME/app-window/x11-window-capture`. It needs a C11 compiler, Xlib headers
and libXcomposite.so.1. It uses XComposite >=0.2, not a root screenshot or crop.

Start managed media with `stream.sh start --screen-policy app-window` (optionally
`--record`). Do not start a second camera owner. The full supervisor still requires
a real connected Kinect and current producer data; this feature does not change
that readiness contract. Its broker uses the explicitly configured profile/output.

In a second terminal, use the locked activity project to run:

```sh
python window_share.py PROFILE_HOME OUT_DIR list
python window_share.py PROFILE_HOME OUT_DIR share --window-id EXACT_ID
python window_share.py PROFILE_HOME OUT_DIR shutter
python window_share.py PROFILE_HOME OUT_DIR resume --window-id EXACT_ID
python window_share.py PROFILE_HOME OUT_DIR status
```

Use `uv run --frozen` for those Python commands. The IDs above are operator-selected,
not examples to copy into a running session. Selection binds UID, PID creation time,
XID, dimensions, display/server generation and broker boot nonce. Closing/unmapping,
resizing, losing the helper, changing server identity or restarting the broker
requires explicit selection/resume; no automatic disclosure after recovery.
Shutter returns only after serialized frame deletion and public metadata clearing.
It cannot retract already recorded/transmitted pixels; the consumer clears on its
next read and independently enforces a two-second frame TTL.

## Qualification record

Native X11 canaries were exercised on the task-owned Hermes/Xfce display: exact
green rectangle and fixed-background counts, zero blue occluding-sibling pixels,
Unmap/Destroy latching and foreign-client-machine rejection. Test source is
`services/hermes-activity/tests/test_native_window.py`; it deliberately requires
an explicitly designated disposable display, because its fixture controls that
display's client-list property. Never run it on a production desktop.

The real installed Hermes browser tool navigated public example.com and returned
its accessibility snapshot. The installed Hermes CUA backend discovered the
dedicated display's windows and captured the exact public test terminal (937x559).
No LLM conversation, provider credentials, robot/MCP call or private page was needed.
One CUA cursor-overlay warning was observed; exact app capture still succeeded.

The physical Kinect was absent from `lsusb -d 045e:02c4`. The full supervisor
correctly failed its bounded capture restart budget and cleaned up; this is not
camera-ready acceptance. Browser/app preview acceptance instead used the real
broker -> Godot -> isolated OBS on native X11, with the camera visibly offline.
No static image or fake camera health was substituted.

Private artifacts live under `/tmp/opencode/furbomek55/`, including a task-only
profile, logs, frame exports and OBS configuration/recording. They are not source
or credentials to publish. Final revisions, checks, decoded recording metadata and
independent review are appended during closeout.

## Rollback and ownership

Agents own rollback: shutter first, stop only this session's OBS recording and
owned processes, select `--screen-policy off`, and retain the older text/timeline
behavior. The existing managed unit and production profile were not rewritten by
this implementation. Do not replace their config with QA data. Generated private
state remains outside Git; every delivered source/config change belongs to the
issue branch. No firewall, network listener, public stream, login enablement,
hardware reset, firmware, wiring or unrelated package change is part of WP-55.

Primary capture semantics: [X.Org Composite protocol 0.4](https://www.x.org/releases/X11R7.7/doc/compositeproto/compositeproto.txt),
especially hierarchy storage and NameWindowPixmap. Named storage survives unmap,
which is why lifecycle invalidation must not be replaced by a frozen last frame.

## Qualification checkpoint, 2026-11-10 UTC

- Activity suite with explicitly owned Xvnc `:28` and actual Godot: **141 passed,
  zero skipped**. Native helper and canary compile with `-Wall -Wextra -Werror`.
  The separate no-camera aggregate passed gateway121, activity135 (four native
  tests deliberately skipped there), supervisor19 and snapshot3, plus real Godot
  consumer fixtures, Ruff ALL, formatting, strict basedpyright and lock checks.
  Later consent-race/private-mode regressions are included in the141 result.
- LSP servers remain unavailable under the user's previous declined-install
  decision. Compiler, parser and strict CLI type checks supply the evidence.
- Recorded output: `media/recordings/2026-11-09 23-35-16.mkv` under the private
  artifact root above, **429.966 seconds,1920x1080,H.264,30 output FPS,AAC**.
  Full `ffmpeg -v error -i FILE -f null -` decode exited0.
  SHA256: `f0314f8cb54238db9564d9e1e5207f304c64f7eed80272952577fd755db34d89`.
- Native app was explicitly shared at06:38:46 UTC; shutter at06:39:11;
  resume at06:39:46; owned broker STOP/CONT at06:41:22–26; selected app unmap/remap
  at06:41:45–49. Broker restart at06:38 started shuttered and required a fresh grant.
  These are runtime observations, not a claim of autonomous privacy classification.
- Full-frame exports `program-{browser,app,shutter,resume,stale,recovered,unmapped,remapped}.png`
  were decoded from that recording and personally inspected. The selected app is
  visible only in live states; shutter/stale/unmap show no last-frame pixels.
  Camera remains visibly OFFLINE in every frame. No current reference-fidelity or
  physical Kinect requalification is claimed.
- A frame-permission regression failed under umask0 before repair, then passed:
  pending/ring JPEGs now use0600 even with a permissive caller. This final
  permission-only change does not change the renderer or captured pixel content.

## Independent review remediation, 2026-11-10 UTC

The first five-lane review was **not an approval**: visual/goal and hands-on QA
passed, but code/security/context lanes found release blockers. They correctly
identified the exported Python broker's legacy desktop fallback, permissive
helper admission, non-atomic boot/resume clearing, post-shutter cleanup races,
resident helpers after revocation, and uncaught process-disappearance races.
An ABI-width correction in the native canary had also advanced the PR beyond
that first review snapshot. Neither the old green CI nor visual passes waived
those findings.

Remediation is in `9734517`, `a8e3e83`, `9f3f25c`, and the source qualification
checkpoint **`df6c3cce66e8fcefcc772c320da11c9c853553b1`**:

- The broker accepts only actual `OFF`/`APP_WINDOW` enum values before output
  creation. Its generic desktop-capture branch is removed. Old positive desktop
  activation tests now exercise supported window freshness/cadence and refusal
  to treat observer release as window consent; no coverage was deleted.
- Helper file and directory must be current-UID, non-symlink and owner-only.
  The profile directory must not be group/world writable. Child environments
  contain only the required display/auth variables, not provider credentials.
- Boot/share/resume/shutter clear public pixels under the same commit lock.
  The CLI no longer deletes frames after unlocking. Revocation and capture
  failure close/reap the helper; ordinary process-exit races are skipped safely.
- A frozen exception could turn a capture failure into a traceback-assignment
  TypeError. Its exception fields remain writable, with a context-manager
  regression. Real subprocess tests cover fragmented reads, EOF, timeout,
  process reaping and descriptor cleanup rather than only a duplicate decoder.
- Twelve review regressions failed before repair; an additional writable-profile
  regression also failed before its guard. At the exact source checkpoint,
  **159 activity tests passed, zero skipped**, with native `:28` and actual Godot.
  Ruff ALL/format, strict basedpyright and lock validation pass as well.

The eight-state recording was repeated after these production edits, not reused:

- Private durable directory: `/data/furbomek-media/window-preview-55/`.
- `2026-11-10 00-20-58.mkv`: **56.833seconds,1920x1080,H.264,30 output FPS,AAC**;
  full ffmpeg decode exited0. SHA256
  `f0bc517f9c7d04a9d917d6f5200481b00a4a95d14f277e1869478667749ddf5f`.
- `review-{browser,app,shutter,resume,stale,recovered,unmapped,remapped}.png` are
  all fresh full-frame exports. Every state was personally inspected. The
  driver also verified no helper child remained after shutter or unmap.
- The first stale-frame export landed just after recovery; a16-frame timing
  sheet located the actual stale interval, and the final stale export uses
  video time26.5s. This was an evidence-sampling correction, not a product fix.
  `stale-timing-sheet.png` and `requalification-times.json` preserve the timing.
- The original429.966s recording,40.966s smoke and their images were also copied
  into this owner-only durable directory. Private artifacts are never published.

The independent re-review must target this remediated source (or a later
documentation-only descendant) and these fresh eight frames. The disconnected
Kinect and separate-account GitHub approval remain explicit external release
limits; neither CI nor a model's review overrides branch protection.
