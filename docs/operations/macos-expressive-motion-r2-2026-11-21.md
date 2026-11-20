# Reduced-preflight expressive firmware

On 2026-11-21 the operator authorized a Mega-only update, confirmed physical
POWER OFF and connected the body USB. The prior
[supported pass](macos-expressive-firmware-2026-11-20.md#first-supported-motion-pass)
verified normal DISARM for Poke, then stopped Defensive Brace on a timeout.

The revision verifies each unique leg target before the first waypoint.
Brace and tuck now need 30 joint-limit checks each instead of 84. Poke
needs eight instead of 24. The target coordinates, trajectory order, speed,
host budget and firmware cutoff are preserved. Native tests verified that
every moved target was checked and that an invalid target or interruption
prevents further movement.

The safety scan and native suite passed on Brodex. Two independent builds
produced identical Mega images. The handheld image matched the previously
installed build byte for byte.

| Artifact | SHA-256 |
| --- | --- |
| Mega HEX | `0f9276e5a88ff5d27dbd3aeafa9582852fee0eea60e523f7bf9e36eaa93130cf` |
| Mega ELF | `f65f64e10aeae0a2dc13aed37c8f72ffc8ec34a4895f0334c3dd11315bc8e9c9` |
| Mega full flash before | `d1ff551bd46346ccbd97ae1d97068c3fae4b3615092fbfb0f0d0bab29445dd92` |
| Mega full flash after | `09afb8ff4645481d3b75d53f51b34bd28ce7a9537cf8d14d9e24a71223dee713` |
| Mega EEPROM before and after | `c7b4f2f7e8e5dae2a53aa146f64f868ec17c9744e9833d13f844c378ae4ad9b1` |

AVRDUDE 7.1 used the established `wiring/m2560` serial-bootloader method at
115200 baud and confirmed signature `0x1e9801`. A fresh no-write verify
matched the saved 262,144-byte flash and 4,096-byte EEPROM. A private
57,344-byte rollback prefix preserves the preceding version across all pages
that this write could alter. The `-D` application-only write verified all
57,290 bytes. A full readback confirmed the new application, every flash
byte outside it and all Mega EEPROM bytes. The handheld received no write.

With POWER still OFF the exclusive local test bridge reported BOOT, idle,
fault 0 and 0.0 V. Powered verification requires the untethered chassis on
its support, with the operator at POWER. The live Hermes profile stays
within its existing action allowlist.

## Supported powered retest

The operator confirmed the body USB was unplugged, the chassis was
supported and still at power-on, and they were at the cutoff. The handheld
reported healthy BOOT at 8.13 V and ARM-only verified DISARM. All four
requests completed with verified normal DISARM during one power-up.

| Action | Gateway round trip | Approximate video position | Logitech observation |
| --- | ---: | ---: | --- |
| Active | 1,102 ms | 00:34 | Visible leg extension, with about 7 px of near-front travel. |
| Poke | 784 ms | 00:49 | The brief foot path was too small or obscured in this view to confirm its reach. |
| Defensive Brace | 2,310 ms | 01:07 | The legs visibly repositioned and returned. Near-front travel peaked around 11 px. |
| Tuck preview | 2,400 ms | 01:23 | The legs visibly moved through the tuck and returned. Near-front travel peaked around 15 px. |

The fixed 640 × 480, 15 fps Logitech view shows leg movement with the
chassis supported. Optical flow tracked consistent features within the
visible leg regions and checked the table and chassis for drift. Both
near-front regions returned to within roughly one pixel of their
starting image position. The image plane gives no absolute distance or
full-foot contact measurement. Protocol times are round trips, including
ARM and DISARM. Each gesture has one powered sample on this revision.

The dedicated acceptance bridge went read-only after the retest. The final
powered RF reading was DISARMED, idle, fault 0 and 8.12 V. The operator then
confirmed physical POWER OFF. A read-only RF check got no reply, and the
temporary owner closed. The regular Mac gateway reclaimed the handheld in
read-only standby and returned `prepared_waiting_for_robot`. Qualification
from this pass is limited to the supervised, supported chassis.

| Private evidence | SHA-256 |
| --- | --- |
| `r2-powered-pass.mkv` | `ed396bb075083d5d3e4849d6cd8d2d0a40fe6ed700613f9b065c8a9d6fef34c8` |
| `r2-acceptance-receipt.jsonl` | `1ee218c1bf77b0882b4ebdee55c35be8186f5c4902c85b9927f6d73ab903b94c` |
