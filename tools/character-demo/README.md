# Offline rendered character fixture

`render_demo.py` drives the existing activity broker from a fresh private JSONL
spool, then starts only `character_render_runner.gd`. The runner hosts the shipped
`ActivityPorts` Control in a real renderer. It does not start the camera scene,
Hermes, speech, OBS, or device services. Its input is explicitly synthetic.

Use the locked `services/hermes-activity` Python environment inside an offline,
credential-free worker. Supply a verified native Godot 4.7 executable and a new
output directory writable only by that worker:

```sh
python tools/character-demo/render_demo.py --godot /absolute/path/to/godot --output /private/new-fixture-directory
```

The renderer needs a graphical session; `--headless` is intentionally rejected
because it cannot certify pixels. It uses a 1920x1080 render target displayed in
a 1280x720 window. The default preview enlarges and clips the shipped NOW panel
for readability, with an explicit fixture caption. `--full-canvas` preserves the
native broadcast layout for comparison. Neither changes the production Control.
No desktop screenshot permission is used: captured PNGs come
only from the fixture's own viewport after `RenderingServer.frame_post_draw`.

The six inputs show idle, thinking, speaking, interruption, a rejected attempt to
revive the cancelled speaking identity, and error. Producer arrival offsets vary
relative to the unchanged 120ms broker and 125ms consumer polling intervals.
The renderer captures around ten frames per second, plus publication changes.
It writes bounded fixture frames and timestamps, and exits within 35 seconds.
The driver also closes its owned reader and renderer on failure.

Compare `events.json` producer timestamps with the first matching frame in
`captures/frames.jsonl`, then inspect the actual PNG text rather than trusting the
logged state alone. For the cancelled replay interval, every captured state must
remain interrupted. A positive result is a measured producer-to-rendered-frame
upper bound for these fixtures, including polling and readback. It excludes
display scanout, OBS encoding and real speech; it is not a general latency SLA.
Keep raw artifacts outside Git. A focused video may crop the native NOW panel
for readability but must preserve captured timing and identify fixture input.

The broader `.github/workflows/character-foundation.yml` runs the unchanged
`tools/verify-media.sh` in a disposable Linux worker. Its isolated loopback and
synthetic PTYs support gateway tests, with no external network or physical
devices. Online preparation excludes local build backends; pinned editable
builds happen only after the privilege and namespace boundary is installed.
