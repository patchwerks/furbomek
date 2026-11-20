# Hardware photo evidence

The [2026-10-15 manifest](2026-10-15/manifest.json) records file names, source
hashes and observations. The chassis photograph uses an opaque mask over
the hand and its reflection. The original is preserved in the private archive.

## Robot controller

- [Radio close-up](2026-10-15/robot-radio-closeup.jpg)
- [USB connection and chassis](2026-10-15/robot-usb-and-chassis.jpg)
- [Controller and WLAN](2026-10-15/robot-controller-and-wlan.jpg)
- [FREENOVE marking](2026-10-15/robot-freenove-marking.jpg)
- [Controller overview](2026-10-15/robot-controller-overview.jpg)

These establish the Freenove robot assembly and ESP-01 / ESP8266EX WLAN module.
The main MCU marking is obscured, but the separate USB bootloader readback now
reports ATmega2560 signature `1e 98 01`; see [firmware records](../firmware.json).
Do not ask for these photographs again or require a readable MCU photo as a
substitute for the recorded signature/readback evidence.

## Earlier handheld remote

- [USB overview](2026-10-15/remote-usb-overview.jpg)
- [Shield overview](2026-10-15/remote-shield-overview.jpg)
- [V4.1 marking](2026-10-15/remote-board-v4.1-marking.jpg)
- [Lower board side](2026-10-15/remote-control-board-side.jpg)

These are the earlier remote assembly, not the robot controller. Preserve this
distinction: a remote's board revision is not the robot's revision.

## Exposed POWER control and rear-right-leg report, 2026-10-16

The [new manifest](2026-10-16/manifest.json) preserves three more original photos:

- [Clear cover shifted](2026-10-16/controller-clear-cover-shifted.jpg)
- [POWER button and V3.1 marking](2026-10-16/power-button-v3.1-closeup.jpg)
- [Reported rear-right extension fault](2026-10-16/rear-right-leg-reported-extension-fault.jpg)

The accessible blue/white POWER pushbutton is now observed on the installed
controller, and its adjacent revision label reads V3.1. This supersedes the
earlier unreadable-revision and hidden-control notes. Do not infer ON/OFF from
the plunger position alone. The leg image records an asymmetric position and an
operator-reported symptom; it does not establish the mechanical/electrical cause.

## Publishing camera evidence

1. Save and retain the original outside the repository in the private archive.
   Publish measurements and a written account when they are sufficient.
2. Export a fresh derivative with a tight robot-only crop or opaque masks that
   cover each person for the full affected interval. Include hands, fingers,
   limbs, clothing and silhouettes, faces, reflections and screen images.
   Cut any frame where you cannot reliably cover a person. Use only the
   reviewed video stream. Remove audio, subtitles, data, source metadata
   and chapters. Keep capture sidecars, thumbnails and original files private.
3. Inspect the exported still or **every frame** of the exported clip at
   full resolution, including cuts and first and last frames. If any human
   part is visible or uncertain, re-export it or publish text only.
   Automated detection can help locate regions to inspect.
4. Record the final file's SHA-256 and path in
   [reviewed-media.sha256](reviewed-media.sha256) after review. Record
   the provenance and any masks/cuts in the evidence manifest.
   Stage the artifact and the updated digest, then run
   `bash tools/verify-public-media.sh` before committing. Run
   `bash tools/verify-public-media.sh <commit>` on each outgoing
   commit that changes media before pushing. Never stage a raw file
   in an intermediate commit.

Apply the same visual review to GitHub issue and PR attachments, release
assets and workflow artifacts before upload. The repository check verifies the
bytes of tracked common image and video formats. It cannot inspect the pixels
or intercept uploads through the GitHub UI. Review media embedded in PDFs,
SVGs and archives before publishing those containers.

Git history can retain an earlier file after a replacement. The redacted
chassis copy addresses the current tree. The earlier original may still
be available through historical revisions or copies.
