---
created: 2026-11-19T20:30:00Z
branch: codex/macos-bring-up
author: Codex
status: active
---
# Table walking and media checks

## Untethered tabletop travel

The pinned vendor archive shows `CrawlForward()` dispatches one call to
`Crawl()`. From sleep that can first establish Active posture. With the
default two-step gait, each call moves one alternating tripod. The prior
bare-table test sent just one call and then cut servo power through normal
DISARM. It demonstrated posture change with unclear travel.

The operator confirmed a clear bare table, untethered robot, physical
POWER OFF, and presence at the cutoff. The handheld UART opened over USB.
The untethered robot did not answer RF while off. After the operator
confirmed power-on stillness, the local test required healthy Guard status
and in-range supply. One armed session executed Active and two successive
bounded forward phases, with acknowledgments at approximately 941, 834
and 930 ms. The test kept the existing heartbeat/deadline logic and verified
DISARM at the end. No firmware was changed. The operator confirmed POWER OFF
after the recording ended.

The fixed optical recording has 42 native frames. Chassis features between
frames 14 and 41 shifted right 4.06 px and up 1.34 px in the 640×360 analysis
view, with 39 inliers and a 1.065 scale factor. A fixed background ROI had
27 inliers, median displacement about 0.03 px and a 1.001 scale factor.
The footage and image expansion support a short advance toward the camera.
Absolute distance, repeatability, and autonomous travel remain unqualified.
The user reported that pressing the power switch afterward pushed the
chassis down. That occurred outside the captured interval. The recorded
Guard log SHA-256 is `414cd0eaa421f9fa424ed0337ac8f8befd2d08a5b78bd98b82efc32240066d0e`.

## Stream program

- RGB video uses a fixed full-frame optical shot and robot-only targeting
  for the inset. This view keeps the same framing through target loss and
  shows the unprocessed optical pixels for movement review.
- The HUD uses Ioskeley Mono Regular v2.2.0. The official archive was
  SHA-256 checked, and the redistributed font includes its OFL notice.
- The rebuilt native capture estimates a surface basis from compatible
  adjacent measured samples. Godot uses round opaque depth-tested points,
  directional surface shading and an off-axis measured XYZ view. XYZ
  translation, registered color, invalid slots and native 512×424 count
  remain intact. One post-deployment snapshot held 72,323 valid points
  at about 14.46 capture fps. At this angle the robot has missing measured
  surfaces. Use the optical shot for travel evidence.
- The dedicated Brodex Chrome test used a fresh anonymous profile with a
  loopback debugging endpoint. Hermes navigated a fresh tab to X.com.
  Headless Chrome returned HTTP 403. Standard headed Chrome showed the
  site's public sign-in page. The Mac received only the selected tab's
  bounded JPEG frames over SSH. Godot presented the live feed in the left
  HUD port and expires it on loss of freshness. This test leaves the
  broker's desktop-capture policy in place.
- A 7.9-second private OBS program recording at 1920×1080 and 30 fps showed
  X's public sign-in page beside the fixed robot shot. The verifier saw
  43 fresh browser frames in 7.5 seconds. The dedicated profile's temporary
  browser connection setting was restored. The browser and its relay were
  closed and the live port cleared. After switching RGB to direct optical
  pixels, a separate 1920×1080, 30 fps OBS recording confirmed the final
  fixed shot. OBS returned an unconfirmed recording start despite producing
  that file. The stop command and subsequent status confirmed OBS idle in
  the test profile. No public stream was started.

## Deployed forward cycle and public stream follow-up

On 2026-11-20 the Mac gateway was updated so one Hermes `forward` request
uses one ARM, two sequential Forward EXECs, and one final verified DISARM.
The first phase must complete while healthy and leave time for the next EXEC
and heartbeat. The other actions still send one EXEC. The 128 gateway tests
passed, including PTY wire-order, low-lease and first-phase fault cases. The
Mac LaunchAgent was reloaded with the local bench closed and the Brodex
Hermes profile rediscovered its seven tools. No USB bridge was opened, motion
requested, or firmware altered. This follow-up verifies the software path.

The XYZ renderer returned to fine rounded dashes with lighter directional
shading. Selecting XYZ no longer changes the camera angle. A private
1920×1080 OBS capture verified XYZ and the fixed RGB stage. A matching native
frame and registration map showed sparse measured depth in the robot's face
and body region. Adjusting the shader does not fill those gaps.

The requested live Twitch broadcast ran from 14:47:42 to 14:48:19 Bangkok
time, with the muted fixed Kinect RGB shot and Hermes HUD. OBS recorded
successful ingest, 903 output frames, and 24.4% rendering lag. It verified
stream stop. The exact dedicated Twitch bandwidth-test settings were
restored and OBS reopened idle with the fixed Kinect source bound.

## Overhead camera and motion scoring

The external webcam was identified as a Logitech Webcam C930e by the Mac's
USB tree and AVFoundation. An early 1280×720 request and an unspecified
resolution both enumerated the camera without delivering frames. Selecting
640×480, 15 fps and `yuyv422` worked. The private, video-only sample has 121
frames in 8.022 seconds. Its SHA-256 is
`6f2d5beb566efcb28b19636b97113873e91d410dfcdb7084464fa2f07521704f`.

The preview shows the chassis from above at an angle. The robot's nearest
feet and near table boundary are cut off. The camera can observe local
chassis motion, but it cannot verify the robot's clearance in this framing.
For a calibrated trial, the camera needs a rigid position above a contained
area, a measured stationary reference, and a rigid chassis target.

A read-only OpenCV check selected chassis and background features in the
recording. It tracked them forward and back and fitted separate robust
transforms. All 105 samples after the reference frame had both estimates.
Stationary chassis p95 was 0.084 pixels and 0.010 degrees of image rotation.
An offline edit moved the chassis 12 pixels right, 7 up and rotated it by
6 degrees. The estimate was 11.98 pixels right, 7.01 up and 5.95 degrees,
with 147 inliers. A separate synthetic camera bump registered 10.77 pixels
in the background. These results establish image-space scoring on this clip.
No hardware motion, metric calibration, continuous observer, or automatic
motion admission was exercised. The Kinect, OBS, and robot control were left
as they were before the webcam check.
