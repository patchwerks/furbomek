# Robot USB identity and installed-image preservation

Observed on Brodex, 2026-10-15. Read root `AGENTS.md` and
[`hardware records`](../hardware/README.md) first. This is an agent runbook, not
an instruction to make the operator repeat completed discovery.

## Completed evidence

- Original robot and remote [photos](../hardware/evidence/README.md) are committed.
- Freenove chassis/controller; ESP-01 module marked ESP8266EX.
- CH340 USB, 115200 baud. Echo `80 00 81` returns `80 01 81`.
- Wiring/STK500v2 bootloader reports MCU signature `0x1e9801` (ATmega2560).
- 262144 flash bytes and 4096 EEPROM bytes were read, then independently verified
  by AVRDUDE rereading the controller. Both operations exited zero.
- Flash contains `Freenove Hexapod Robot` at `0xb231`, `ATmega2560` at `0x3e0e4`
  and `Arduino explorer stk500V2 by MLS` at `0x3e0ef`, in the upper boot region.
- After exiting the bootloader, the application echo still returned `80 01 81`.
- No flash/EEPROM writes, chip erase, fuse/lock changes or motion commands issued.

Hashes and complete metadata are in [`firmware.json`](../hardware/firmware.json).
The hash identifies the installed image even though its source release is unknown.
Do not confuse the bootloader's reported programmer version `2.10` or embedded
`Mar  7 2013` string with the application version or installation date.

## Tool provenance and host changes

AVRDUDE was absent. Ubuntu package `7.1+dfsg-3build2` and runtime libraries were
downloaded with `apt-get download` and extracted using `dpkg-deb -x` under
`/tmp/opencode/avrdude-7.1-readonly/root`. No package was installed system-wide.
Package SHA-256 is recorded in `firmware.json`; AVRDUDE reported version 7.1.
The invocation explicitly supplied the extracted `etc/avrdude.conf` and temporary
`LD_LIBRARY_PATH`; no config or persistent device-permission change was made.

Dependencies: `libftdi1` 0.20-4ubuntu3, `libhidapi-libusb0` 0.14.0-1build1,
`libusb-0.1-4` 2:0.1.12-35build1. Existing system libraries supplied the rest.
Consult [version-matched options](https://avrdudes.github.io/avrdude/7.1/avrdude_3.html)
before reproducing a command. Temporary binaries are not a deployment dependency.

## Read-only method

**Actuator energy was physically disconnected by the operator.** Opening serial
or entering/leaving the bootloader resets the board and can run servo startup
code. Reconfirm current physical isolation before any future session. Do not
assume historical test conditions still hold. No concurrent serial owner was
found before the read. Keep one exclusive operator/process during this procedure.

The essential AVRDUDE arguments were:

```sh
# These assume the version-verified tool/config is supplied by the agent.
# Signature only: all commands use no-write and disable auto-erase.
avrdude -n -D -p m2560 -c wiring -P /dev/ttyUSB0 -b 115200 \
  -U signature:r:-:h

# Read into a NEW private directory, never overwrite the preserved baseline.
avrdude -n -D -p m2560 -c wiring -P /dev/ttyUSB0 -b 115200 \
  -U flash:r:flash.bin:r -U eeprom:r:eeprom.bin:r

# A second device read verified the saved files without modifying the MCU.
avrdude -n -D -p m2560 -c wiring -P /dev/ttyUSB0 -b 115200 \
  -U flash:v:flash.bin:r -U eeprom:v:eeprom.bin:r
```

The actual commands used `timeout --signal=TERM 120s`, the extracted absolute
binary/config/library paths and absolute private output paths. The readback used
`sudo -n -u lock -g dialout` for scoped device access; group membership was not
changed. The signature probe used `sudo -n`. `-D` implies `-A`, retaining trailing
erased bytes so the raw flash file spans the full expected address space.
Never add `-e`, `-F`, `:w:`, oscillator calibration, or interactive terminal mode
to this preservation procedure.

## Private artifacts and rollback

On Brodex the preserved baseline is:

```text
~/.local/state/furbomek/firmware-backups/2026-10-15/
  flash.bin       262144 bytes
  eeprom.bin        4096 bytes
  readback.log
  verify.log
```

Directory mode is 0700; files are 0600. These runtime/device artifacts are not
source/configuration and must not be added to Git or Chezmoi. Copy them to
approved private backup storage before any later destructive firmware operation.
Do not publish unknown binary dumps or calibration data. The photos, in contrast,
were explicitly authorized by the operator for repository storage.

No device-memory change was made, so no restoration was needed. **Restoration has
not been tested.** A serial bootloader may not expose protected bytes and can
synthesize signature/fuse/lock responses. Fuse/lock state is not captured. Full
file size and upper boot strings are useful readback evidence, not a guarantee
that a bootloader-erasing failure is recoverable over USB. Preserve ISP recovery
options before any bootloader/fuse change. No such change is currently authorized.

## Next safe programming step

Do not ask for the same photographs again. Use the preserved evidence, confirmed
Mega2560-class USB programming path and vendor schematics to review servo/output
mapping and power behavior. Prepare a reproducible safety-firmware artifact and
simulator tests before considering a write; retain the baseline and explicitly
record restore limitations. Robot-local command expiry/watchdog, STOP, inactive
reset outputs and interlocks must be implemented and exercised unpowered before
a supported-bench, independent-cutoff powered test. Hermes motion remains gated
on those tests, not on discovering a human-readable stock version number.
