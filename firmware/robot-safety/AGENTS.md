# Robot safety package guide

This directory is a project-owned, actuator-disabled diagnostic package. It is
not the installed robot firmware, a motion controller, a hardware-in-the-loop
test, or an authorization to connect a controller.

## Scope

- Keep all changes for this component under `firmware/robot-safety/`.
- Do not access a serial device, flash memory, EEPROM, fuses, lock bits, or a
  bootloader from this package.
- Do not add vendor firmware, Arduino startup code, servo libraries, gait code,
  radio code, head code, raw GPIO operations, or output-enable flags.
- The AVR image may configure only UART0, Timer1, and reset-cause capture.
- The capability bitmap is permanently zero. `LEASED` means protocol ownership
  only and never means physical arm or actuator permission.

## Build rules

Use `build.sh` with native GCC 13.3 and the extracted AVR toolchain supplied by
`AVR_ROOT`. Normal builds do not download or install packages. Build products
belong in `/tmp` or an explicitly supplied output directory, never in source.

Use `test.sh` and `check-safety.sh` before handoff. The common code is C++11
for AVR, has no heap, RTTI, exceptions, or host-library dependency, and every
module stays below 250 pure source lines.

## Safety contract

Boot/reset is `STOP_LATCHED`. STOP is unconditional, priority ordered, safe
before reply, and idempotent. Lease expiry uses unsigned 32-bit elapsed time.
Malformed, stale, duplicate, unknown, CRC-failed, rate-rejected, and transport
fault input cannot extend a lease. A sticky UART overflow or framing/overrun
fault requires hardware reset before any buffered command can be considered.

The source does not enable or disable the hardware watchdog. Actual inherited
watchdog state from the preserved bootloader has not been measured on
hardware. This package does not claim physical safe posture or power-cut
guarantees. Those require later measured, unpowered, supported-bench, and
independent-cutoff acceptance outside this directory.
