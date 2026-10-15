# Kinect v2 host-side point-cloud stream

**Audience: future agents.** The user does not read or execute these runbooks.
Operate the stack, recover it and run QA yourself; report outcomes rather than
handing the user the commands below. Read the scoped `AGENTS.md` files first.

## Reference-detail revision

The presentation now uses the supplied sideways video after upright rotation as
its visual contract: fine crimson sampled detail, actual tracked magenta corners,
an amber measured-depth probe and linked processed/optical mini windows. The
default high-detail field samples the **native 1920×1080 optical frame**, not
invented high-resolution depth. Its caption says `COLOR SAMPLES / DEPTH-PROBED`.
Native measured XYZ remains available with `3`/`4` and orbit keys; those modes
retain sensor gaps and the true 512×424 depth resolution. Do not claim exact
human-scene pixel parity from the robot-bench camera view.

Capture now publishes all **217,088 native depth slots**, not the first bring-up's
54,272 subsampled slots. Four immutable ring snapshots carry matching geometry,
registered RGB, native optical RGB and registration-map sequence IDs. The real
tracking sidecar uses pinned MediaPipe pose/face models, measured depth-region
components and a private ORB/RANSAC template for the actual robot. Native paired
delivery of roughly **29–30 FPS** was observed in the revised bench scene.

Agents start all four components through the same host launcher: capture,
tracking, renderer and OBS. OBS is now **1920×1080 / 30 output FPS**. Preserve its
existing profile/collection and operator-entered destination settings. The
left read-only public-activity port accepts bounded canonical character events
and same-directory PNG previews for future Hermes/A2UI/Glimpse adapters; it is not
a deployed Hermes broker or an A2UI protocol implementation. Missing real input
remains `AWAITING PUBLIC ACTIVITY`. See the renderer `AGENTS.md` for its exact
event contract. No agent tasks should be fabricated to populate the window.

## Working path

**Observed on Brodex, 2026-10-14:** Kinect v2 → native libfreenect2 OpenGL capture → private shared-memory MultiMesh frames → Godot 4 point-cloud window → OBS XComposite capture → NVENC H.264 local recording. The VM is not required for this media path and remains intact and powered off.

From this repository, launch the already-built host stack:

```bash
bash tools/kinect2/launch-host.sh
```

To begin a local recording immediately:

```bash
bash tools/kinect2/launch-host.sh --record
```

Do not launch a second capture process. The launcher rejects a second host session. Close OBS to stop the launcher-owned capture and viewer. In a running OBS session, use its **Start Recording / Stop Recording** button; **F10** also stops recording. Recording is not public broadcasting.

The Godot window provides **1** color-sampled RGB, **2** color-sampled crimson,
**3** measured XYZ depth palette, **4** measured XYZ crimson, **[ / ]** stroke
size, **arrow keys** measured orbit, **wheel** zoom, **O** bounded measured orbit,
**R** reference-presentation reset and **Esc** close viewer. Invalid measured
depth remains absent; the native depth count is labelled separately from visual
samples. Expired matched tracking snapshots clear the main surface, brackets,
probe and camera imagery within the 600ms TTL rather than retaining stale content.

OBS uses the isolated **Kinect2** profile and collection under `/data/furbomek-media/obs-config`; it does not alter the user's normal OBS profile. The launcher updates the point-cloud window selector while preserving saved profile and collection settings. To broadcast, set your platform/destination and stream key in this profile's **Settings → Stream**, then use **Start Streaming**. No destination or key was supplied or guessed, and no public stream was started by the agent. Keep keys out of Git.

## Installed/build requirements

This bring-up targets Ubuntu 24.04, an active X11 desktop and working NVIDIA OpenGL. It uses Godot **4.7.2**, libfreenect2 **v0.2.1** at `fd64c5d9b214df6f6a55b4419357e51083f15d93`, and OBS **32.2.2**. The driver reports internal version `0.2.0`; the release tag is still `v0.2.1`.

```bash
sudo apt-get install --no-install-recommends \
  build-essential cmake pkg-config curl unzip nodejs \
  libusb-1.0-0-dev libturbojpeg0-dev libglfw3-dev libgl-dev
bash tools/kinect2/build-host.sh
sudo install -m 0644 services/camera-capture/70-furbomek-kinect2.rules \
  /etc/udev/rules.d/70-furbomek-kinect2.rules
sudo udevadm control --reload-rules
```

Install OBS separately from its official Ubuntu 24.04 release package. Brodex already has the verified package installed. Its existing artifact is `/data/furbomek-vm/artifacts/OBS-Studio-32.2.2-Ubuntu-24.04-x86_64.deb`, SHA256 `b6557ca2059287210332accc94c267094050489cffffc5c832e746e3a418dab0`. The Godot archive SHA256 is `cadd3204e728a35d3f13adb7fd0d7902636b79f6b95c40c265eb73b6c35329e4`; `build-host.sh` checks it before extraction.

The udev rule uses `0660` plus systemd's `uaccess` tag, not world-writable USB permissions. The active local desktop user receives the ACL. Unplug/replug applies it to future device nodes; an existing device can receive it with a targeted `udevadm trigger --action=change /sys/bus/usb/devices/PORT` followed by `udevadm settle`, using the actual port from `lsusb -t`. Do not reset the entire USB controller. Headless/service accounts are **not** granted access by this rule; they require a separately reviewed group-based policy.

The launcher defaults to Brodex's current `DISPLAY=:1` and `/run/user/UID/gdm/Xauthority`; override `DISPLAY` and `XAUTHORITY` when launching from another actual desktop session. `FURBOMEK_MEDIA_ROOT` defaults to `/data/furbomek-media`; the caller must own that directory. `FURBOMEK_KINECT_DIR` defaults to `/dev/shm/furbomek-kinect2-UID` and is owner-only. No renderer, capture service or OBS WebSocket listener is exposed on the network.

## Capture contract

`services/camera-capture/kinect2.cpp` owns the physical camera once. It receives
native 1920×1080 color plus 512×424 IR/depth, applies factory registration and
publishes all 217,088 native slots. Invalid/non-finite/out-of-range depth is
hidden; XYZ is in metres with Godot's Y/Z signs flipped. Independent distance
accuracy is not yet measured. The additional color-sampled presentation is an
explicit optical styling layer, not a new source of measured depth.

`track.py` runs as the ordinary user through its pinned `uv` script environment.
Its versioned Pose Lite and BlazeFace model hashes are checked before use. The
private robot template is agent-seeded from observed live camera pixels at
`/data/furbomek-media/models/robot-template.png`, with a same-sized annotated
`robot-template-mask.png` excluding background corners; never commit either.
The observed homography transforms this object mask before deriving the true
registered/optical ROI. Do not cosmetically shrink a HUD box to hide a loose
data ROI. Missing calibrated optical mappings remain nullable and hide optical
overlays/crops instead of inventing a whole-frame mapping. A template match
has an explicit `orb_inlier_ratio`, not a general semantic-class probability.
People/faces are separately model-detected; do not relabel a depth component as
a person. Positive public model fixtures detected one pose and one face; the
live bench verification used the actual robot, not an unobserved human subject.

`latest.bin` is atomically replaced: four little-endian uint32 header fields (`0x32434b46`, version `1`, publication sequence, instance count), then 16 float32 values per slot (12 row-major Godot transform values + RGBA). The Godot reader bounds the slot count at the native depth pixel count. This host-only ABI assumes little-endian float32 and is not a network protocol. Masks, point arrays and per-frame geometry do not enter A2UI or OSC.

The owner-only `metadata.json` records publication sequence, valid/colored point counts, received IR mean, native dimensions, paired delivery FPS, sensor depth-sequence gaps and a **host receipt** monotonic timestamp. Sequence gaps mean depth frames not represented in this paired consumer; they do not by themselves establish USB packet loss. Host receipt time is not a measured glass-to-program latency.

## Evidence and limits

Reference-detail QA additionally exercised real robot-template withdrawal and
reacquisition, a tracker pause with color/native mode toggles while stale,
automatic recovery, a clearly marked public text/image fixture, and rejection of
an allowed-source event carrying an invalid image path. Fixtures were removed;
the live activity port returns to awaiting actual public events. The recorded
program is checked visually as well as decoded: OBS 32's old `scale_ref=1280×720`
initially caused a 1.5× crop after the canvas upgrade. The final setup sets both
absolute and relative transforms for true 1× full-HD capture, preserving the
other profile/collection settings. Do not treat earlier cropped test recordings
as proof that the mini windows are on air.

The contour-led revision is recorded in
`/data/furbomek-media/recordings/2026-10-14 14-39-22.mkv`: **108.266 seconds,
1920×1080 H.264 at 30 output FPS**, fully decoded, with fresh eight-state exports
named `revised-program-{live,xyz,lost,reacquired,stale,recovered,activity,rejected}.png`.
The main shader and magnifier now use local edges/contrast and sparse flat-wall
occupancy; the robot mask drives the data ROI before HUD projection. An
all-unmapped calibration module check returned null optical ROI/probe; a real
headless scene execution verified both optical crops and color-mode bracket
projection hidden while valid measured XYZ stayed available. The temporary
fixture was removed after that check. Do not mistake these scoped checks for a
physical calibration accuracy or live-human recognition qualification.

The latest closure run is
`/data/furbomek-media/recordings/2026-10-14 15-03-41.mkv`: **91.600 seconds,
1920×1080 at 30 output FPS**, fully decoded. Its eight current exports are
`accepted-program-{live,xyz,lost,reacquired,stale,recovered,activity,rejected}.png`.
The invalid-path case was held for more than four seconds while the previous
valid fixture still had a 20-second TTL; the recorded rejected state visibly
returned to `IDLE` with no preview. The preview is now palette-limited, the
processed window is a smaller actual-probe detail crop, and mapped object-mask
outliers are robustly trimmed before ROI publication. The environment retains
subordinate source-luminance surfaces instead of either static noise or an
empty black wall. Additional module checks verified a partial map chooses a
real mapped probe. Actual headless scene executions verified both all-unmapped
and known-ROI/missing-probe cases, retained XYZ, rejection of incomplete activity
payloads, and acceptance of complete control payloads. Temporary fixtures were
removed. Activity title/summary/status/tool are required; no ACTIVE default is
invented. Do not reuse the earlier mistimed rejection exports as proof.

MediaPipe code is Apache-2.0; use the versioned Google model bundle URLs and
checked hashes in `build-host.sh`/`track.py` rather than floating downloads.
See [MediaPipe source license](https://github.com/google-ai-edge/mediapipe/blob/v0.10.21/LICENSE),
[upstream model-license clarification](https://github.com/google-ai-edge/mediapipe/issues/6306),
and [OpenCV license](https://github.com/opencv/opencv/blob/4.11.0/LICENSE).
The robot template and object mask are private project camera-derived assets,
not redistributable fixture photos or model weights committed to this repository.

- Native USB-device passthrough in the existing VM enumerated the sensor but failed capture after a 90-second timeout with packet-sequence and virtual xHCI transfer errors. No persistent VM passthrough was left installed.
- Native host capture runs as the regular desktop user, not root. The saved initial log records **8,212 frames at 14.9825 FPS**, more than **9 minutes** of registered RGB/IR/depth delivery before the deliberate restart/failure tests. Roughly **27,000 valid** and **23,000 non-black registered-color** points were present in the current view.
- A **96.966-second**, **1280×720 / 30-fps** NVENC H.264 MKV was produced by OBS and decoded end-to-end. Different recorded virtual-camera views showed real parallax. The OBS output rate does not imply 30 new sensor frame sets per second.
- The final launcher was used on the real desktop; RGB/crimson/depth controls and stale-feed disappearance/recovery were driven through its actual window. Private logs, screenshots and recordings are under `/data/furbomek-media`, outside Git.
- The final build also produced a fully decoded **237.833-second** recording, `recordings/2026-10-14 10-46-53.mkv`, containing all palette and stale/recovery states. Two independent read-only code/visual reviews inspected the final source and all four extracted states and returned PASS with no blockers.
- This is a working media bring-up, not completion of the plan's 30-minute 1080p qualification, independently measured depth accuracy, exact reference-video effects, tracking/HUD, robot control or full autonomous Furb-o-Mek deployment. Those gates remain separate.

## Machine GitGov change record and rollback

This entry records the Brodex machine changes for this bring-up alongside their owning project source:

- **Commands:** apt installed the OpenGL/GLFW/libusb/TurboJPEG development dependencies, the verified OBS 32.2.2 release package and `xdotool` for native-window QA. No packages were upgraded or removed. The existing stale-NVIDIA-firmware autoremove suggestion was ignored.
- **Files:** project capture, renderer, OBS-configuration helper and launch/build scripts; generated owner-only assets/configuration under `/data/furbomek-media`; `/etc/udev/rules.d/70-furbomek-kinect2.rules` sourced from the project and staged explicitly in etckeeper.
- **Verification:** native `-Werror` build; Godot parser/runtime/shader launch; Node syntax/diagnostics; Bash syntax and CLI happy/error paths; systemd 255 `udevadm verify`; live uaccess ACL regenerated after removing the temporary manual ACL; live camera/renderer/OBS recording and decoded video.
- **Recovery preserved:** no VM deletion, host reboot, GDM restart, GPU/controller passthrough, firewall changes, SSH/Tailscale/RustDesk changes or public listeners. Capture/viewer run without root, Hermes credentials or robot authority.
- **Rollback:** close the isolated OBS session first. Remove only this project's udev rule, reload udev, and reconnect the Kinect to discard its device ACL. Keep the VM and existing OBS/user profiles intact. Remove `/data/furbomek-media` only after preserving any wanted private recordings. Remove `obs-studio`, `xdotool` or the newly installed development packages only if no other application now needs them; do not run a broad autoremove.
- **Publication:** project source, reproducible tooling and agent instructions are published in the Furb-o-Mek GitHub history when authorized by the user. Private recordings, local robot templates/masks, generated OBS configuration and downloaded models remain outside that repository. The installed system rule is separately staged in etckeeper; do not publish unrelated `/etc` state into GitHub. Apt's pre-existing etckeeper hook automatically made commit `99cfa1b` before the first install and its configured remote push failed authentication; no remote/config repair was attempted as part of this camera task.

Primary references: [libfreenect2 pinned source](https://github.com/OpenKinect/libfreenect2/tree/fd64c5d9b214df6f6a55b4419357e51083f15d93), [Godot MultiMesh buffer](https://docs.godotengine.org/en/4.7/classes/class_renderingserver.html#class-renderingserver-method-multimesh-set-buffer), [Godot release](https://github.com/godotengine/godot-builds/releases/tag/4.7.2-stable), [OBS release](https://github.com/obsproject/obs-studio/releases/tag/32.2.2), [systemd v255 camera uaccess policy](https://github.com/systemd/systemd/blob/v255/rules.d/70-uaccess.rules.in).
