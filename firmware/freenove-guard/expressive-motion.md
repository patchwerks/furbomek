# Expressive motion candidate

The initial software candidate was built on 2026-11-20 in the isolated
`codex/expressive-motion-candidate` worktree from published `origin/main`
at `931d9d5`. The Mac deployment branch contains the later installation
and physical test records.

| Candidate action | Wire value | Fixed trajectory |
| --- | ---: | --- |
| `poke` | 8 | Lift the reference front-right foot 5 mm, reach 7 mm forward, pause for 140 ms, retract and replant. |
| `defensive_brace` | 9 | Lower 5 mm, step outward 4 mm per side using alternating tripods, hold 250 ms, then restore the initial stance. |
| `tuck_preview` | 10 | Lower 7 mm, step inward 6 mm per side using alternating tripods, hold 250 ms, then restore the initial stance. |

Distances are commanded offsets in the vendor reference frame. Physical foot
identity, clearance, loaded support, speed and motor timing require a hardware
test. The brace and tuck do not shift a grounded foot sideways in the planned
trajectory. The tuck is a short compact gesture. A persistent compact rest
requires a validated return-to-standing transition.

The AVR adapter verifies that its internal foot targets are in a standing
range and checks every proposed target against the existing inverse-kinematics
limits before sending any waypoint. It checks the terminal fault between
waypoints and uses the existing operation deadline and hardware cutoff. Failed
preflight or motion enters the existing terminal fault path. No coordinates,
speed controls or raw servo arguments are exposed to the gateway. The
three candidate names use the existing explicit local action allowlist.

## Build evidence

Brodex ran the Guard safety scan and native suite, including all eleven wire
actions, footprint timing and the interruption and refusal cases. The candidate
gateway passed 125 tests, including the PTY cases for exact wire values and
default allowlist refusal. Ruff and configured basedpyright passed.

Two independent AVR build directories produced identical application artifacts.
The [Arduino bundled package index](https://github.com/arduino/Arduino/blob/master/hardware/package_index_bundled.json)
supplied the archived GCC 7.3.0 toolchain checksum. The existing build verified
the pinned Arduino core, vendor archives, flash limits and AVR output policy.

| Candidate artifact | SHA-256 |
| --- | --- |
| Mega HEX | `7de1946726fadccdc5b2e335e5379e3fbefc205f2cfa172e19b8331389276b54` |
| Mega ELF | `5e4e15f95ef25f9a7316bc2ee0b50907517f066a5be2cb8712164d601b90ce7b` |
| Handheld HEX | `840934a268f93cee31f11bae196ab4fff1e97fd09b7501b6c14bc0d1677ae39e` |
| Handheld ELF | `4a9aa9f61f4010a5bddf0a5ba9d18b531d68d83f01bd0dfe1137e91f40949ae2` |

An independent Intel HEX scan verified checksums, non-overlapping records
and the last application addresses of `0xdbc1` for the Mega and `0x3c49`
for the handheld. Both are below the existing build limits. This file check
does not establish either installed board's fuse or bootloader settings.

A private native build of AVRDUDE 7.1 at upstream source
`2e0be1e1aedfc10c904712bddda37e36356e7a66` is ready on the Mac. Its help
output verified the version without opening a device. The backup and
verification procedure still requires the two physical USB connections
and current OFF confirmation.

The Mega and handheld images must be qualified together because the handheld
decoder shares the command range. Before any update, identify and preserve both
installed images and EEPROM using the
[wired maintenance procedure](../../docs/operations/robot-wired-maintenance.md).
The first powered test uses the supported chassis and the operator at POWER.
Measure actual foot identity, posture, travel and terminal stop response before
allowing the new actions in the live profile. Keep the Mac's persistent bridge
and two-phase Forward when carrying the host action mappings into the live
checkout.

## Reduced preflight revision

In the first supported trial the initial Mega build completed Active and
Poke. Defensive Brace exceeded the host budget and STOP acknowledged
FAULT 4. The revised candidate preflights each distinct Cartesian target
once for its exact leg. Brace and tuck check 30 targets out of 84 visits.
Poke checks eight out of 24. The fixtures verify every executed target
has a matching validation and that rejection or interruption prevents
further movement. Pose paths, speeds and guard limits are preserved.

Two independently built Mega images matched. The Mega HEX SHA-256 is
`0f9276e5a88ff5d27dbd3aeafa9582852fee0eea60e523f7bf9e36eaa93130cf`.
The new Mega ELF SHA-256 is
`f65f64e10aeae0a2dc13aed37c8f72ffc8ec34a4895f0334c3dd11315bc8e9c9`.
The handheld HEX matches the original expressive build. Powered timing
and visible gesture acceptance use separate installation records.

## Larger gesture revision

The 2026-11-21 Mega revision uses a 14 mm lift and 17 mm reach for poke,
a 9 mm drop and 10 mm outward target for brace, and a 12 mm drop and 11 mm
inward target for tuck. These are commanded offsets. The supported checks
completed and verified DISARM for all three gestures. Bare-table testing of
this revision was deferred.

The Mega HEX SHA-256 is
`07f2e7149bf6945c4b9b9015a70e536a6639e28ea768d6eb2a44dd7f13a06ca3`.
