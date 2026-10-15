# Current robot records

- [`hardware.json`](hardware.json): installed hardware observations, measurements,
  unknowns, and safety qualification.
- [`firmware.json`](firmware.json): installed-image identity, inspected reference
  source, safety findings, flash/rollback state, and firmware change history.

Use strict JSON, with context in named fields rather than comments. `null` means
unknown, not absent or safe. These are evidence records, **not activation config**.
Keep observations, reference/platform inferences, and verified installation facts
separate. Neither generic CH340 enumeration nor an echo identifies the firmware.

## Mandatory maintenance

Every agent changing or discovering robot hardware, wiring, power, radios, MCU,
firmware, bootloader, calibration, or safety behavior must read and update these
records in the same change. Update `updated_on`, the relevant facts and provenance,
and append firmware history for programming/configuration changes. Record:

1. before/after state and exact board/firmware revision or explicit unknown;
2. method, date, raw protocol evidence or measurement and units;
3. safety implications, test conditions, checks performed and checks not performed;
4. artifact hashes, programming method, rollback procedure and its limitations.

Preserve meaningful history; do not overwrite an old measurement with a new guess.
Keep secrets, USB serial numbers, network identities/endpoints, unknown binary
dumps, private media and logs outside Git. Hardware photos explicitly designated
by the operator for repository evidence belong in [`evidence/`](evidence/README.md)
with provenance and hashes, not only temporary paste storage. Commit metadata and
hashes rather than raw firmware dumps with unresolved provenance. Stage only
task-owned paths.

## Verified bring-up, 2026-10-15

The operator first connected the handheld remote. Its close-ups show “Smart Car
Remote Shield” and “Control Board V4.1”; these are **not** robot-controller markings.
After moving USB to the robot controller, Brodex enumerated a CH340 bridge and a
115200-baud, 8N1 probe sent `80 00 81`, receiving `80 01 81`. Actuator power was
reported disconnected. No motion command or firmware write was sent. Device node
`/dev/ttyUSB0` is a historical observation, never a stable identity.

Subsequent no-write bootloader probing reported ATmega2560 signature `1e 98 01`.
The installed 262144-byte flash and 4096-byte EEPROM were backed up privately and
independently verified against a second device read. Their hashes and embedded
Freenove/STK500v2 identifiers are in `firmware.json`. The application echo still
passed afterward. The installed source release remains unknown, but the installed
image is now identified by its hash; do not repeat identification or demand more
photos merely because the exact release label is absent.

The inspected vendor source lacks local command expiry/link-loss STOP; a host-side wrapper
cannot repair that failure boundary. Do not reconnect actuator power as a result
of a successful echo. Current hardware identification and safe programming gates
are listed in `firmware.json`. The [readback runbook](../operations/robot-readback.md)
records commands, private backup locations, evidence and rollback limits.

## Primary reference evidence

Inspected vendor revision:
[`1596c5ffe07a262fa7dc6d0189de6c2321270278`](https://github.com/Freenove/Freenove_Hexapod_Robot_Kit/tree/1596c5ffe07a262fa7dc6d0189de6c2321270278).
The [`FNHR archive`](https://github.com/Freenove/Freenove_Hexapod_Robot_Kit/blob/1596c5ffe07a262fa7dc6d0189de6c2321270278/ArduinoLibraries/FNHR.zip)
contains the robot implementation; its source header says V12.6 / 2023-09-19.

- `FNHR/src/FNHRComm.cpp`: serial initialization/parser (96–115), echo/voltage
  dispatch (346–358), action-related auto-sleep (568–579), periodic service
  (678–686). No serial-age deadline or link-loss cancellation in this path.
- `FNHR/src/FNHROrders.h`: echo and voltage orders; no version query or
  unconditional STOP command.
- `FNHR/examples/Default/Robot/Robot.ino`: `robot.Start(true)` and `robot.Update()`.
- [`Processing client`](https://github.com/Freenove/Freenove_Hexapod_Robot_Kit/blob/1596c5ffe07a262fa7dc6d0189de6c2321270278/ProcessingApp/Communication.pde):
  115200 baud, two-second startup wait, echo handshake and frame delimiters.
- [Vendor assembly warning](https://docs.freenove.com/projects/fnk0031/en/latest/fnk0031/codes/tutorial/Assembly.html):
  startup/restart can rotate servos.

The vendor source is a reference, not a dump or identification of this controller.
Its noncommercial/share-alike license needs review before incorporating code into
this streaming-robot project. No vendor firmware was copied into this repository.
