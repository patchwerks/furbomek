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

## Side-view setup and recovery

The Logitech was moved beside the robot. During setup, the handheld
USB device re-enumerated at the same path with a different device
node. The old session's reads failed. The Mac reopened the handheld
after the owner confirmed physical POWER OFF. Illumination from
beside the camera made the side links visible. The 720p side preview
supplied about 10 frames per second with capture timestamps that
can be compared with Kinect and command timestamps.

The next power-on produced RF BOOT, idle, fault 0 at 7.81 V. The
ARM-only check did not complete and issued STOP before sending any
motion command. The last powered status showed FAULT 4, the STOP
latch. That status identifies the cutoff action. The preceding
rejected reply was missing from the original runner output.

The owner confirmed physical POWER OFF and the body remained
untethered. The Mac reopened the handheld with the updated runner
that preserves the original rejected guard reply. No application
write was made during the recovery.

## Untethered 18° and 30° passes

The next start reported BOOT, idle, fault 0 at 7.82 V. ARM-only and
Active each returned to DISARMED. The earlier ARM rejection did
not recur. Sixty-two additional probe commands completed in
0.90–1.32 s and each ended DISARMED, idle, fault 0. The body USB
remained unplugged. The owner confirmed physical POWER OFF at
handoff.

The table lists the largest completed command in each direction
relative to the Active reference. Each cell reports negative and
positive command degrees.

| Firmware leg | Hip yaw (− / +) | Femur (− / +) | Knee (− / +) |
| --- | ---: | ---: | ---: |
| 1 | −30° / +30° | −30° / +18° | −30° / +30° |
| 2 | −30° / +30° | −30° / +6° | −30° / +30° |
| 3 | −30° / +30° | −30° / +6° | −30° / +30° |
| 4 | −30° / +30° | −30° / +18° | −30° / +30° |
| 5 | −30° / +30° | −30° / +6° | −30° / +30° |
| 6 | −30° / +30° | −30° / +6° | −30° / +30° |

The Kinect recorded 13–20 matched color and depth frames for every
larger probe. The Logitech recorded 9–14 timestamped frames for 60
of the 62 probes. The two +18° femur runs used the Kinect's
front view, which showed the front feet lowering with table clearance.
The remaining +18° and all +30° femur commands need verified
clearance beneath each foot. The command table describes this
supported test arrangement.

On leg 1, the Kinect image shows approximately +26° and −23°
of **projected** knee travel during the two 30° commands. The
hand-marked pivot was near (1329, 398) in the 1920×1080 image.
The positive probe used tip positions near (1352, 581) and
(1431, 554) in frames 1574 and 1590. The negative probe used
(1353, 581) and (1280, 571) in frames 1600 and 1610. These
are approximate image-plane angles measured from each trial's
starting pose. Depth was missing at the pivot at both peaks and
the oblique second view did not consistently resolve the same
toe through the sweep. Calibrated physical angles for the 18
joints and actual mechanical endpoints remain open.

## Paired 36° firmware installation

The owner confirmed physical POWER OFF and connected both USB
devices. The Mac released its prior handheld session and identified
the Mega and handheld by bootloader signature. Fresh backups of both
applications and Mega EEPROM matched the prior verified readbacks.
The temporary firmware pair came from source revision `326da84`.

| Board | App bytes | Full flash SHA-256 before | Full flash SHA-256 after |
| --- | ---: | --- | --- |
| ATmega2560 body | 60,276 | `f931a90915c53523f800d91ee4126037f979edb2d57e0bbe72853af57a84ea69` | `03732df4c1c4d0215ce53b987b203599139ffa7b32c7e0337d4fcd23d19f1065` |
| ATmega328P handheld | 15,504 | `411b28c105d9ab040d18a8095df7707a31f441ba9525cdd83723dc7e185a8b0d` | `aace026de169730108403ce82ace218f3456a7f29197f1bdc2e1a9693d20c50c` |

Both applications matched independent full flash reads. All bytes
outside the declared application ranges matched their backups. The
Mega calibration EEPROM matched its backup byte for byte. The
handheld EEPROM is outside readback scope because its bootloader
aliases EEPROM reads to flash. Both writes targeted application
flash only with AVRDUDE 7.1 and `-D`. Full backups and the prior
application pages are available privately for wired rollback.

With physical POWER OFF, RF STATUS from the Mac's held handheld
session returned BOOT, sequence 0, idle, fault 0 and 0.0 V. The
untethered motion, speed comparison and supported height tests
were pending at this checkpoint.

## Untethered 36° sweep and speed comparison

The owner confirmed the body USB was unplugged, the robot stayed
still at power-on, and the chassis was supported. The Mac saw only
the handheld. RF reported BOOT, idle, fault 0 and 7.83 V. ARM-only
and Active returned to DISARMED.

The supported test exercised yaw and knee on every leg in both
directions at ±36°. Each of the 24 axis and direction combinations
completed once at each speed. The faster pass used the reverse order.
Eight additional front-knee repeats brought the probe count to 56.
All probes ended DISARMED, idle, fault 0. The Kinect and Logitech
timestamps covered every command window in the 48-probe comparison.
Footage and recordings remain in the private archive.

| Trajectory step | Median time through verified DISARM | Range |
| --- | ---: | ---: |
| 3.0 mm per 20 ms | 1,303 ms | 1,299–1,323 ms |
| 3.75 mm per 20 ms | 1,202 ms | 1,199–1,223 ms |

Every matched direction took less time at 3.75 mm. The median
per-direction reduction was 100 ms, with a range of 77–121 ms.
The elapsed interval includes the session, arm, return, fixed
camera holds and verified disarm. It measures the whole probe.

For the leg 1 positive knee probe, the Kinect tracked the right
edge of the leg silhouette in a fixed region of the image.
The time between 10% and 90% of the outbound optical sweep was
388 ms median at 3.0 mm from three usable clips (372–402 ms)
and 336 ms median at 3.75 mm from four clips (298–358 ms).
The metric uses projected displacement and includes the
intermediate holds. The physical endpoint angle, load and
tabletop gait speed remain unmeasured.

The low and middle presets also completed with verified DISARM.
The side view showed the feet retract and return while the chassis
stayed fixed on the support. The high preset adds 10 mm of
downward foot travel from middle. The views could not establish
the required 15 mm clearance under every foot. A taller support
was requested for the high trial. The loaded tabletop test remains
pending.

## High stance and return interruption

The owner confirmed the taller support, untethered body and
stillness at power-on. ARM-only and Active each verified DISARMED.
High completed in 1.101 s with verified DISARM. The two camera
views showed the feet extending downward while the chassis stayed
on the support. The separate return to middle failed after 0.198 s.
The host sent STOP and the guard reported latched fault 4. The
owner confirmed physical POWER OFF, with the body USB absent.

The pinned Freenove inverse and forward kinematics reproduced a
boundary failure in a single-precision harness. The −25 mm high
target can yield a computed −25.000001907 mm foot position. The
original return preflight rejected that value. The old gate
rejected eight of 16 round trips at the preset bounds. The fix
allows up to 0.001 mm of numerical roundoff at either boundary and
clamps the input to the original range before planning the path.
The harness accepts all 16 cases under the corrected gate. Native
coverage also rejects an actual excursion past the tolerance.
The high-to-middle sequence still needs a powered rerun with the
corrected Mega image before the loaded tabletop trial.

Two independent builds produced Mega HEX SHA-256
`afdf42a9e555cd7f483d7683444b1b1484049858bd1174273158551c71020a22`.
The handheld HEX matched the installed image, qualifying a
Mega-only maintenance update after a fresh wired readback.

## Height fix installation

The owner confirmed physical POWER OFF and connected body USB.
The installed Mega full flash and EEPROM matched the
`326da84` readbacks. The Mac retained the prior application's
page-aligned rollback image. AVRDUDE 7.1 wrote only the corrected
Mega application from `e6c3f1a`. Its independent full flash
readback confirmed all 60,342 application bytes and matched
the backup outside that range. The calibration EEPROM matched
the backup byte for byte. The handheld port stayed held throughout.

| Artifact | SHA-256 |
| --- | --- |
| Mega full flash before | `03732df4c1c4d0215ce53b987b203599139ffa7b32c7e0337d4fcd23d19f1065` |
| Mega full flash after | `9d5cc2b1ac89f13938d122bcbf1de9e89f8cf675c6e33fd8e12220dd664e1123` |
| Mega calibration EEPROM | `c7b4f2f7e8e5dae2a53aa146f64f868ec17c9744e9833d13f844c378ae4ad9b1` |

With physical POWER OFF, the held handheld returned RF BOOT,
sequence 0, idle, fault 0 and 0.0 V. The untethered return-to-middle
and loaded tabletop tests were pending at this checkpoint.

## Corrected high-to-middle sequence on support

The owner confirmed the body USB was unplugged and the robot
stayed still at power-on. The handheld reported BOOT, idle, fault
0 and 7.79 V. ARM-only and Active both verified DISARM. The
Kinect and Logitech recorded two high-to-middle cycles on the
taller center support. All four height commands finished and
reported DISARMED, idle, fault 0. The two returns took 1.223 s
and 1.102 s. The camera views showed the feet extending at high
and retracting on return while the chassis stayed supported.
The previously observed return fault did not recur. The owner
was cued to move to the bare table with physical POWER OFF.

## Loaded height sequence on the bare table

The owner confirmed the body USB was absent, the support was
removed, and Furbomek was still on the clear tabletop. The Mac
verified the handheld was the sole USB serial connection. The
guard reported DISARMED, idle, fault 0 at 7.78 V. A fresh ARM-only
check and Active passed. Low, middle, high and the final return
to middle all completed with verified DISARM and fault 0. The
four height commands took about 1.00–1.12 s each. The owner
confirmed physical POWER OFF with the body USB absent at handoff.

The two cameras covered all four commands. In the Kinect image,
three chassis patches showed the following median vertical shifts
relative to frame 8696, the middle stance immediately before high.
The depth column reports median camera-space Y from registered depth
points near the tracked chassis patch at pixel (1141, 553) in that
reference. Positive values indicate upward displacement.

| Preset | Sample frames | Image displacement | Depth displacement from middle |
| --- | --- | ---: | ---: |
| Low | 8170, 8171, 8173 | −14 px | About −8 mm |
| Middle | 8186, 8188, 8189, 8696 | +1 px | Reference |
| High | 8710, 8712, 8713 | +21 px | About +10 mm |
| Final middle | 8727, 8728, 8730 | +4 px | About +2 mm |

The low-to-high span was 35 pixels and approximately 19 mm along
the Kinect's vertical axis. The measurement uses one small registered
depth neighborhood with six to ten returned points per frame. Sparse
tabletop depth prevented a reliable table-plane fit, so absolute
ground clearances remain unmeasured. The side view corroborated the
body rising and lowering. The robot stayed upright in both views.
After the final DISARM, the camera still showed a small offset from
its original middle stance. This was a stationary loaded pose test
with brief holds. Long holds and walking at the different heights
remain unmeasured. The camera files remain in the private archive.
