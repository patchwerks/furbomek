# Original hardware photo evidence

The operator explicitly requested that the supplied photos be committed, not
left in temporary paste storage. The [2026-10-15 manifest](2026-10-15/manifest.json)
maps all nine original uploaded JPEGs to descriptive filenames and SHA-256 hashes.
The uploaded bytes are preserved without recompression. EXIF and visible content
were reviewed before committing; no GPS EXIF fields were present.

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

For later operator-designated hardware evidence, preserve the files and add
provenance, hashes and observations in the same commit series. Never keep the only
copy under `/tmp`. Do not automatically publish other private media or firmware
dumps; preserve those privately and commit only permitted metadata.
