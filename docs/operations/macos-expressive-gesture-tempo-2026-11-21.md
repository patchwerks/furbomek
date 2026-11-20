# Larger expressive gestures

The [Hermes tabletop pass](macos-brodex-edge-2026-11-20.md#supervised-bare-table-pass)
established command completion, but the owner observed that the gestures
looked like jitters. The revision increases foot travel and gives entry,
hold and return different timing. It uses the existing three command names.

| Gesture | Commanded path | Nominal stepping and hold budget |
| --- | --- | ---: |
| Poke | Lift the front foot 14 mm, reach 17 mm, hold 240 ms, then retract and plant it more slowly. | 580 ms |
| Defensive brace | Drop 10 mm, widen 9 mm per side through alternating tripods, hold 300 ms, then settle back. | 1,080 ms |
| Tuck preview | Drop 11 mm, pull each side in 12 mm through alternating tripods, hold 360 ms, then return to standing. | 1,200 ms |

The values are commanded offsets and modeled update times. They do not
measure elapsed time, observed displacement or joint load. The fastest
waypoint increment is 5 mm per nominal 20 ms update. The existing 2.5 s
host action budget and 3 s firmware cutoff remain in force. Footprint changes
keep the existing lift-before-shift rule and the exact target preflight.

The native suite checked the strokes, slower returns, target preflight,
tripod sequence and interruption behavior. An independent model using the
[Freenove reference geometry](../hardware/vendor/freenove/INDEX.md) checked
6,290 foot samples along the compiled trajectories from five starting pose
variants, with a minimum modeled joint margin of 2.3°. Both Brodex builds
matched byte for byte. The handheld HEX matched the installed version.

| Candidate artifact | SHA-256 |
| --- | --- |
| Mega HEX | `07f2e7149bf6945c4b9b9015a70e536a6639e28ea768d6eb2a44dd7f13a06ca3` |
| Mega ELF | `05fa457494c0ffef5bbdd0b1510e0916cf7ce27d7c76ec622660b04d9ab94bd3` |
| Handheld HEX | `840934a268f93cee31f11bae196ab4fff1e97fd09b7501b6c14bc0d1677ae39e` |

## Installed Mega and motor-off check

The owner authorized the Mega-only update and confirmed physical POWER OFF
and body USB. AVRDUDE 7.1 reported signature `0x1e9801` and independently
verified the preceding full 262,144-byte flash and 4,096-byte EEPROM before
writing. A private 57,600-byte application prefix preserves the touched
pages for rollback. The application-only write verified all 57,552 bytes.

The full readback matched the new application and the preceding image
outside its application range. The Mega EEPROM comparison passed.

| Verified memory | SHA-256 |
| --- | --- |
| Previous Mega full flash | `09afb8ff4645481d3b75d53f51b34bd28ce7a9537cf8d14d9e24a71223dee713` |
| New Mega full flash | `6c9f593fb45a6f04a5d0408896cca1a284b6a34773163c936d259315b3229db5` |
| Mega EEPROM before and after | `c7b4f2f7e8e5dae2a53aa146f64f868ec17c9744e9833d13f844c378ae4ad9b1` |

The regular Mac gateway held the same read-only handheld connection through
the update. Its motor-off RF check returned BOOT, idle, fault 0 and 0.0 V.
The following powered pass needs the body USB unplugged and the operator
at POWER. Timing and camera evidence from the previous firmware belong to
that earlier image.

## Powered supported pass

The operator confirmed the body USB was unplugged, all legs were clear on
the center support, and power-on was still. The Mac reused its held
handheld connection. ARM-only verified DISARM with a reported 8.08 V.
All motions completed on one power-up, each with verified normal DISARM.

| Motion | Local round trip | Approximate clip start | Kinect observation |
| --- | ---: | ---: | --- |
| Active | 1,095 ms | 00:00 | Visible extension into the starting pose. |
| Poke | 889 ms | 00:02 | Visible front foot lift and reach. A screen-left joint region traveled about 37 px at peak. |
| Defensive brace | 2,396 ms | 00:04 | Visible alternating lift and widening. A screen-right joint region traveled about 49 px at peak. |
| Tuck preview | 2,416 ms | 00:07 | Visible contraction and return. A screen-right joint region traveled about 66 px at peak. |

The front Kinect supplied 159 matched optical frames. Image-plane
tracking used fixed-camera background compensation. The center support
carried the chassis, so foot travel here does not establish loaded tabletop
motion or a metric displacement. The existing action budgets were used.
The regular Mac gateway held USB as the test window expired. The radio
reported DISARMED, idle and fault 0 in read-only standby.

| Private evidence | SHA-256 |
| --- | --- |
| `larger-gesture-supported.mp4` | `5cee83c6af0e3acaed3f4bbf3c3cc929d8ec47080530b39186647bd37ded8822` |
| `actions.jsonl` | `a7b3c5f537ba16e47da13e492d486d6868d8abd94e1f23f017be9ae3c01e2b4e` |
| `frames.jsonl` | `0fe235a947926e82c8be82eb89513944e40145839752e1752b79d549a35b89ef` |
