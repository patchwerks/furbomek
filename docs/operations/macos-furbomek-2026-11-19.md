---
created: 2026-11-19T16:15:55Z
branch: codex/macos-bring-up
author: Codex
status: active
---
# macOS Furb-o-Mek bring-up

This session used an Apple M4 Max MacBook on macOS 26.6 and an isolated
worktree based on `931d9d5082e512d6cd753bdf2ea3b1c15afcc8bc`. The robot and
Kinect were local to the Mac. The `furbomek` Hermes profile was verified on
Brodex. The supported bench test and media checks used separate device owners.

## Supported robot movements

The operator confirmed the robot was unplugged from charging and physically
powered off before serial access. Disconnecting the handheld identified its
serial bridge. The first local USB/RF read returned BOOT, fault 0, idle and
reported 0.0 V. Two subsequent preflight opens lost transport. The operator
moved the handheld to another USB port and closer to the robot. An exclusive
serial connection then passed the off-state gate with the Kinect idle.

The operator placed the chassis on its center support with all legs free and
stayed at the independent POWER cutoff. With physical power applied, BOOT
remained idle at a reported 8.22 V. One ARM-only transaction sent no gait
command, verified DISARM and was reported still by the operator. The existing
local `PoweredActionRunner` then executed Active, Sleep, Forward, Backward,
Left, Right, Turn Left and Turn Right one at a time. Each received completion
and a matching healthy DISARM acknowledgment at a reported 8.21–8.22 V. The
operator confirmed all eight motions looked right on the support.

The operator switched physical POWER OFF. Final protocol state was DISARMED,
fault 0, idle, sequence 118 and reported 0.22 V. The serial owner closed its
port normally. Protocol voltage is supplementary to the physical power report.
The private bench log SHA-256 is
`073fb0128bd59eb18cac84bdb7522d7ca40a89ce922d172c8ba69350ad03dd2a`.

The [installed firmware records](../hardware/firmware.json) continue to describe
the prior verified images. This session built only host camera software. It
performed no firmware readback, programming, robot reset, EEPROM or calibration
write. Emergency STOP, watchdog-reset behavior, floor travel, head motions,
direct robot USB, stock Wi-Fi control and unattended operation were outside
this acceptance.

## Native media

The Kinect enumerated on USB SuperSpeed. The native arm64 build used the
project-pinned [libfreenect2 v0.2.1 source](https://github.com/OpenKinect/libfreenect2/tree/fd64c5d9b214df6f6a55b4419357e51083f15d93),
OpenGL, CMake 4.5, libusb 1.0.30, GLFW 3.5.1, pkgconf 3.0.11 and
TurboJPEG 3.2.1. CMake 4 needs `CMAKE_POLICY_VERSION_MINIMUM=3.5` for that
driver. The Godot 4.7.2 Universal release matched its published SHA-256
`c58a24e31d720be9d62f60cb5627c4e695fb72f21b0cfe1bc9ccaa9a3b3ba63e`.
The Python 3.12 tracker used the pinned MediaPipe 0.10.21, OpenCV 4.11 and
hash-checked model files.

The first 20-second capture delivered 295 synchronized RGB, IR and depth
frames. The first build failed on exit. libfreenect2 takes ownership of the
packet pipeline passed into its open call. Giving it an owned heap object
restored exit code 0 on two consecutive capture and restart runs. The pinned
driver deliberately resets the sensor when capture closes on macOS and reports
`LIBUSB_ERROR_NO_DEVICE` during interface release.

Darwin C++ steady time and CPython monotonic time use different epochs on this
host. Before the fix the capture age appeared negative, so tracking never
published. After stamping capture with `CLOCK_UPTIME_RAW`, the real tracker
published matching fresh frames. The capture settled near 14.9 paired FPS
with 1920×1080 RGB and 512×424 depth/IR. The 14-minute run delivered 12,572
registered frames and exited cleanly. The Brodex template did not lock the
new view. A private template and mask annotated from the Mac's real registered
frame gave a verified `object-furbomek` lock with the measured probe. A
temporary empty mask cleared the lock on the next frame. Restoring the
original mask reacquired the object on the following frame.

Godot respected a windowed launch and rendered full 1920×1080 evidence for the
crimson optical-sampled view, measured XYZ, and XYZ camera orbit. Compared
with the upright reference, the fine crimson detail, magenta tracked
brackets and two linked insets were visible. The scene and subject differed.
No human pose, face lock, metric depth-accuracy or exact reference fidelity
claim follows from the robot view. The live renderer reported about 14.9 FPS
from the sensor independently of the OBS output setting.

OBS 33.0.1 used the separate `Furbomek Mac Test` profile and scene collection
with only the Godot window as a muted source. The initial 30-second 1080p30
recording decoded but showed the macOS title bar and padding. The native
window probe showed the fullscreen viewer filling a 2560×1080 display. The
Mac viewer now opens as a borderless 16:9 window with viewport scaling. The
corrected 21.2-second H.264 1080p30 recording decoded from start to finish.
Its top heading, tracking brackets and both right-hand crops were visible
inside the frame, with no desktop controls or title bar. Peak audio was
reported at −91 dBFS. Its private SHA-256 is
`69c737388a61c41b617f93297975e653e50acb1dcc8c795c84c38b8c8bd1beb8`.

Twitch's secure ingest was reachable. After the operator configured Twitch
locally, the OBS test profile used the verified
[`bandwidthtest=true` ingest flag](https://dev.twitch.tv/docs/video-broadcast).
Twitch accepted the initial live OBS scene for 42 seconds. OBS output 1,280
frames and reported two rendering-lagged frames. The stream stopped and
OBS returned to idle. The corrected framing was checked in a subsequent
local recording. The profile remains in bandwidth-test mode.

The native warning-as-error capture build, 121 gateway tests, 127 activity
tests, three snapshot tests and the headless Godot activity fixtures passed.
Five lifecycle tests in the unchanged Linux supervisor stopped at the default
`/dev/shm` path, which is unavailable on macOS. This bring-up used bounded
foreground workers and a private frame directory. Set `FURBOMEK_KINECT_DIR`
to that directory for the capture executable, tracker and Godot, and set
`FURBOMEK_MEDIA_ROOT` for the tracker's private models. On a new viewer
launch, select the new Godot window in the OBS source because the native
window ID changes.

## Brodex control path

Mac-to-Brodex SSH worked and Tailscale round trips were 263–289 ms. Brodex could
reach Mac SSH, but its existing identity was refused. As an alternative, a
temporary owner-only reverse SSH Unix-socket forward over the existing
Mac-to-Brodex login let Brodex read fresh Mac camera and object-lock status.
The probe socket accepted only a status request and was removed after the
test. This establishes the transport without any new SSH account or key.

The recommended rollout keeps the Mac as the native device and media host.
Keep Hermes and the redacted activity broker on Brodex. Use a restricted
semantic edge service over the verified transport and keep all robot
heartbeat timing local. Actual Hermes-to-Mac control and live HUD delivery
require their own checks. See [the macOS deployment profile](../../PLAN.md#profile-e-macos-device-host-with-a-remote-hermes-harness).
