# Local joint bench diagnostic

Build the Mega and handheld images together with `build.sh --joint-bench`
using the [pinned build inputs](README.md#reproducible-build). The ordinary
application continues to reject joint-probe wire codes. The bench Mega
admits Active to establish a reference stance, then accepts only the
finite probe commands for motion. It rejects probe commands on body USB
and the manual radio route. It retains unconditional STOP and the existing
watchdog and operation deadlines.

The diagnostic selects one leg, one joint axis, one signed direction and
a 6°, 18° or 30° target band. The starting stance is Active with all legs
clear on the center support. Each command preflights three target points
against the installed joint checks and a 45 mm foot displacement ceiling.
One leg moves through those samples with brief pauses and returns to its
starting Cartesian target. The hardware timing, linkage and servo load
still require measurement.

The local Python runner admits no model-facing probe tool. Use its
ARM-only check and Active preflight on the exclusively held handheld
transport. A successful probe requires a healthy powered voltage, ARM
and EXEC acknowledgements, healthy completion and verified DISARM.
Ambiguous or failed operations after BEGIN use terminal STOP. The
body USB is unplugged during powered measurements.

## Measurements

Record the neutral pose, three tracked points on the two links around the
joint, and the points' rectification from pixels to the joint plane. Use
the overhead view for yaw where the hip pivot is visible, and a side view
for the femur or knee plane. The camera reduction compares rectified
angles relative to the recorded starting pose. A camera crop or an
unrectified angle cannot establish a measured endpoint.

Record negative and positive travel separately for each of the 18
chassis axes. Keep each commanded band, observed angle, camera view,
settling behavior and whether the leg returned. Start with the shortest
band and qualify visibility and clearance for each larger band. These
bands are inputs for an incremental measurement. A last observed angle
within these bands is distinct from an absolute servo stop or a physical
maximum beyond the guarded envelope. The latter requires independent
position and load feedback.

Before installing or reverting, preserve and verify both prior images
through the [wired maintenance procedure](../../docs/operations/robot-wired-maintenance.md).
The production images use a narrower command family. Keep their exact
rollback artifacts alongside the paired bench build.

## Build verification

On 2026-11-21, two independent AVR builds produced matching application
images. The native guard checks passed, including diagnostic action
decoding, the transport restrictions and the STOP/TTL interactions. Mac
gateway tests passed with pseudo-terminals and synthetic camera landmarks.
The build checks establish no physical range of motion.

| Application | HEX SHA-256 | ELF SHA-256 |
| --- | --- | --- |
| Mega | `74a5c00a464b4358e2fb310716c2588ca0468a703b00591bad2d82488950af44` | `7954f2366ed3dd263429d62296e459f02bb5c9f3af2fef6a5115a0e5d155925b` |
| Handheld | `8336d68ddf6275c83a53b5667d558346cd6f30d2450ffdd0d4441e548466a095` | `0e0e478804b5dc473bdf14eae7b89c610909b2a4478e8e72679919e1f939b44e` |
