# Joint bench installation and camera preflight

The owner confirmed physical POWER OFF and connected the body USB while
the robot rested on its center support. The Mac released the normal
Hermes bridge before opening either bootloader. The temporary bench build
was compiled from the source recorded in the [joint diagnostic build
record](../../firmware/freenove-guard/joint-bench.md).

## Verified controller installation

| Board | App bytes | Full flash SHA-256 before | Full flash SHA-256 after |
| --- | ---: | --- | --- |
| ATmega2560 body | 59,314 | `6c9f593fb45a6f04a5d0408896cca1a284b6a34773163c936d259315b3229db5` | `f931a90915c53523f800d91ee4126037f979edb2d57e0bbe72853af57a84ea69` |
| ATmega328P handheld | 15,434 | `48c74f21a0902995a20732604eea4eda4dbb95124db1f477236d86d675a74f48` | `411b28c105d9ab040d18a8095df7707a31f441ba9525cdd83723dc7e185a8b0d` |

AVRDUDE 7.1 identified the devices by their bootloader signatures
`0x1e9801` and `0x1e950f` and performed application-only writes with
`-D`. Independent full flash reads matched the candidate application
bytes and matched the original bytes everywhere else. The Mega EEPROM
matched its pre-write baseline
`c7b4f2f7e8e5dae2a53aa146f64f868ec17c9744e9833d13f844c378ae4ad9b1`.
Handheld EEPROM was outside the verification scope because its
bootloader aliases reads to flash. Neither update targeted EEPROM,
bootloader, fuses or locks.

The private backup retains all original readback bytes and both
page-aligned application prefixes for wired restoration with physical
POWER OFF. The exact restoration procedure is
[wired device maintenance](robot-wired-maintenance.md).

## RF and camera preflight

With motor POWER OFF, the private Mac session held the handheld open.
It received an accepted RF STATUS of BOOT, idle and fault 0, along with
0.0 V reported supply. The normal Hermes motion bridge was closed for
the diagnostic. The Mac checks that the body USB is absent before
transmitting any powered probe.

The Kinect produced 18 matched color and registered depth frames in the
preflight sample. Its front view resolves several front leg outlines in
color, while measured depth is sparse around the hip and knee pivots.
The Logitech's higher oblique view shows the support and overlaps the
far-side legs. Each measured angle needs an observable hinge and
adjacent links in an aligned or calibrated view. Powered motion and
travel measurements were pending at this checkpoint.

## Untethered 6° pass

The owner confirmed POWER ON, stillness, support and presence at the
power switch. The Mac saw only the handheld port. RF reported BOOT,
idle, fault 0 and 7.88 V. ARM-only and the Active reference stance
finished in DISARMED.

Each leg received one 6° command in each direction on each of its
three axes. All 36 commands completed in 0.80–1.00 s and each final
status verified DISARMED, idle, fault 0. Frame timestamps overlapped
all 36 command windows with 12–15 color and depth pairs per trial.
The footage and command log remain private.

The front color camera shows the first leg's knee pivot and foot tip.
Tracking those landmarks in frames 8840/8852 and 9551/9562 gives
approximately +4.4° and −5.3° of **projected** excursion. Samples taken
1.5 s after the respective command starts still show approximately
+2.2° and −2.5° of projected displacement from the starting pose.
The image-plane result suggests the foot did not fully settle at its
starting position after DISARM. Verify the neutral return from a
side view before using these moves for calibration.

The front view lacks reliable depth at the pivot and hides several
other joints. Physical travel in degrees remains open for all axes.
The next measurement needs a close view across the leg plane for
femur and knee, and a clear overhead view for hip yaw. Before
increasing the band, check the support clearance and neutral return
from that view. The larger bands and hardware endpoints remain
untested.
