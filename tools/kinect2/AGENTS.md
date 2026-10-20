# Agent-owned Kinect broadcast operations

The user does not operate from runbooks. Agents own building, launching, stopping,
diagnosing, recording, recovery and verification. Do not hand back a command list
as a substitute for doing the work. Ask the user only for physical actions,
unavailable credentials or an actual design decision that tools cannot resolve.

## Read before changes

- Root `AGENTS.md`, `PLAN.md`, `docs/operations/kinect2-host.md`, and the renderer's
  `godot/DESIGN.md`. The operations document is the agent's detailed runbook.
- Host `~/.config/NETWORK.md` before touching any network or remote-access setting.
- The user video is the visual contract, not the first blocky bring-up or a generic
  dashboard. The private attachment is
  `~/.moshi/uploads/ScreenRecording_09-28-2026 18-01-51_1.mov`, SHA256
  `01ed4004af22efb02ed2882f8f8eec6c923dddd419aa056c68f47a80ab0cb01f`.
  Its landscape content is stored sideways: inspect upright reference frames.
  Do not commit the video, camera recordings or private screenshots.

## Runtime ownership

- Host-side capture is the current working path. The VM is preserved and off;
  ordinary VM USB-device passthrough failed. Never delete it or detach Brodex's
  shared USB controller/GPU to work around a media issue.
- `bash tools/kinect2/build-host.sh` rebuilds pinned dependencies and capture.
  `bash tools/kinect2/launch-host.sh` starts capture, tracking, Godot and the isolated OBS
  profile; `--record` starts only a private recording. Default generated state is
  `/data/furbomek-media`, with owner-only volatile frames in
  `/dev/shm/furbomek-kinect2-UID`. The current desktop uses `:1` and the active
  user's `/run/user/UID/gdm/Xauthority`; verify rather than hardcoding a new seat.
- A running agent-owned session is named `furbomek-kinect-host` in tmux. Inspect
  its process ownership before stopping it. Preserve unrelated tmux sessions.
  Close/stop this session's OBS before a controlled rebuild/restart, then verify
  all launcher-owned camera/viewer processes have stopped. Do not run two camera
  owners. Keep OBS profile/collection and any operator-entered destination intact.
- Managed sessions use `bash tools/kinect2/stream.sh` and the locked
  `services/stream-supervisor` module. Clean viewer/OBS exit ends that managed
  session; crashes use bounded restarts. The older `launch-host.sh` remains a
  separate unsupervised path: do not mix launchers or infer its lifecycle changed.
  If the user exited a viewer to use the desktop, do not reopen it merely to check
  status. Check current unit/health and the dated acceptance record instead.
- Never start public broadcasting without the user's requested destination and
  authorization. Do not print or commit stream keys. Do not enable an unauthenticated
  OBS control listener or weaken SSH, Tailscale, UFW, GDM or RustDesk.

## Visual and evidence gates

- Default `2` is a native-1080p color-sampled crimson field for reference-level
  visual detail, explicitly labelled as color samples, not extra measured XYZ.
  `3` and `4` show genuine native-depth geometry; arrows/orbit switch to that
  measured view. `R` returns to the detailed presentation. Never conceal invalid
  measured depth by relabelling optical pixels as independently measured points.
- Magenta brackets in the sampled-color view use the actual tracked native
  optical ROI. The amber probe uses its registered measured pixel. In XYZ mode,
  project the actual measured ROI samples through the camera. Processed and
  photographic insets are same-sequence real camera crops, not canned imagery.
- After renderer changes, record the real 1920×1080 OBS program and inspect clean
  full-frame exports. A desktop screenshot during OBS minimization can contain
  compositor ghosts; a clipped 1920×1011 image is invalid evidence.
- OBS 32 saves relative scene transforms. For this native 1920×1080 input on the
  1920×1080 canvas, `scale_ref` must also be 1920×1080 and `scale_rel` 1×1, not just
  absolute `scale=1`. A stale 1280×720 reference produces an encoded 1.5× crop
  even while the desktop looks correct. `configure-obs.mjs` normalizes only this
  owned item; verify both right mini windows are inside the actual recorded frame.

- Fine crimson points/short strokes and readable contour gaps are required.
  Large solid quads or merely coloring the blocky cloud red do not meet the brief.
- Tracking brackets and optical/processed crops must follow real detections,
  retain IDs, respect TTL and use the stated source frame. Never label an invented
  rectangle `BODY ACQUIRED` or a decorative reticle `FACE LOCK`.
- Side mini windows are reusable presentation slots for camera probes and
  A2UI/Glimpse/Hermes activity. Their contents are read-only and unprivileged;
  missing real activity is idle/unavailable, never fabricated agent work.
- The activity observer/broker produces real redacted text/timeline events.
  Desktop pixels remain unqualified and rejected, not an exception granted by
  private recording. The native X11/OBS program must be inspected: a healthy
  process list did not prevent black XComposite output on the QA virtual desktop.
- Record the actual revised OBS program. Compare upright reference and output
  at the same presentation scale, including motion, brackets and insets. A build,
  static mock or generic visual-QA PASS does not establish reference fidelity.
- Distinguish native depth detail from RGB styling/interpolation and sensor FPS
  from OBS output FPS. Never claim independent metric accuracy without targets.
- Exercise stale feed, tracking loss/reacquisition and source restart. Expire old
  graphics rather than retaining a convincing frozen frame. Leave the working
  stack available to the user after non-destructive QA unless asked otherwise.
