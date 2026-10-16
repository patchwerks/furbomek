# Robot safety diagnostic component

This is a clean-room, project-authored safety kernel and bounded UART
diagnostic shell for an ATmega2560-class target. It is deliberately not
operational motion firmware. It has no actuator-capable code, no servo/head/
gait/radio library, no vendor linkage, no EEPROM access, no flash command, and
no physical-device access.

The shared C++11 code is exercised by native C++17 tests and by a native CLI
driver. The AVR image configures only UART0 and Timer1, using a 16 MHz clock
reference that is not measured on the board. It captures `MCUSR` and clears
that register, but does not enable or disable a watchdog or write fuses or
EEPROM. The diagnostic safe sink has no hardware output implementation.

## Protocol

Frames are:

```text
A5 5A | body_len:u8 | body[body_len] | crc16:u16LE
```

`body_len` is 1 through 24. CRC is CRC-16/CCITT-FALSE, initial value
`0xffff`, polynomial `0x1021`, no reflection or final xor, calculated over the
`body_len` byte followed by all body bytes. The transmitted CRC low byte comes
first.

The command body is little-endian:

```text
version:u8 | opcode:u8 | epoch:u32LE | sequence:u16LE
```

The base body is 8 bytes. `LEASE` adds `ttl_ms:u16LE`, making 10 bytes. The
response body is 14 bytes: the base fields, result:u8, state:u8,
capabilities:u8, fault_flags:u8, and remaining_ms:u16LE.

The four opcodes are `STATUS=1`, `LEASE=2`, `STOP=3`, and
`CLEAR_STOP_LATCH=4`. The only capability bitmap is zero forever.

Version-zero STOP with zero epoch, zero sequence, and no payload is the valid
emergency form and is recognized before normal version, epoch, sequence, lease,
or rate checks. Version-one STOP is also independent of epoch and sequence.
Both call `force_safe()` before latching. A repeated STOP does not advance the
epoch again.

The state machine is:

- `STOP_LATCHED`: the boot/reset state. Only version-one CLEAR with the current
  epoch and sequence zero can move to `DISARMED`.
- `DISARMED`: only a version-one lease with the current epoch and sequence zero
  can acquire a lease.
- `LEASED`: TTL is 50 through 500 ms. Renewals use the current epoch, a
  modulo-16-bit sequence delta in 1 through 32767, and at least 20 ms since
  the last accepted lease.

Expiry calls `force_safe()` first, then moves to `DISARMED` and advances the
epoch. Stop also advances the epoch once when leaving a non-latched state.
Epoch exhaustion fails closed in `STOP_LATCHED` rather than wrapping. Epochs
are finite replay fencing within one boot/session, not indefinite anti-replay
or authentication; modulo-16-bit sequence ordering eventually admits an old
sequence after enough renewals. Fresh boot or session authentication is not
implemented, and no actuation is possible here.

## Decoder and transport behavior

`FrameDecoder` is a fixed bounded nonblocking state machine with a 20 ms
partial-frame timeout. It calls the protocol engine directly; there is no
decoded-command queue. The protocol engine ticks the kernel before every input
byte is decoded, and a native or AVR loop must also call `tick()` before and
between bounded receive batches. The AVR shell uses a 64-byte UART0 RX ring.
RX overflow and UART framing, overrun, or parity errors create a sticky
transport fault, force safe, discard buffered input, and block commands until
hardware reset.

After a complete frame passes CRC and shape checks, `CommandCommitGuard` enters
a short interrupt-critical boundary, claims the current transport-fault state,
and applies the command only when no fault is pending. It restores the saved
interrupt state before encoding or queueing a reply; CRC processing and reply
serialization are never inside that boundary. A fault observed before commit
rejects the command, while a fault raised after commit preserves the accepted
reply and then latches the transport stop before the next command.

Replies are encoded into one bounded frame before the reply sink is asked to
queue them. A busy sink drops the complete reply rather than transmitting a
partial frame. The AVR TX sink sends at most one queued byte per loop tick and
never blocks on UART readiness.

## Build and test

Native only:

```sh
firmware/robot-safety/build.sh --native
firmware/robot-safety/test.sh
```

AVR diagnostic build from the extracted, not system-installed toolchain:

```sh
AVR_ROOT=/tmp/opencode/furbomek-avr-toolchain \
  firmware/robot-safety/build.sh --avr --output-dir /tmp/robot-safety-avr
```

The build requires no package download. It emits an ELF, Intel HEX, linker
map, objdump report, Timer1 disassembly-order report, size report,
undefined-symbol report, hashes, and tool versions. It uses `-mmcu=atmega2560`,
C++11, `-Os`, freestanding compilation,
no RTTI, no exceptions, no thread-safe statics, section garbage collection,
and no build ID. The Timer1 report verifies the actual AVR disassembly sequence
for timer stop, flag clearing, compare setup, CTC mode, clock start, and
interrupt unmask. The default AVR linker map contains an empty `.eeprom`
region of size zero; the image has no EEPROM data section or access routines.
Standard AVR device-info metadata can still name `__eeprom_end`.

Safety source scan:

```sh
firmware/robot-safety/check-safety.sh
```

The native CLI is a real parser-plus-kernel driver:

```sh
firmware/robot-safety/build.sh --native --output-dir /tmp/robot-safety-example
/tmp/robot-safety-example/native/robot-safety-driver --help
printf 'clear\nlease 100 0\ntick 19\nlease 100 1\nstop\nquit\n' | \
  /tmp/robot-safety-example/native/robot-safety-driver
```

It also accepts `bytes HEX...` for malformed/raw input and `fault` for the
sticky transport path. It is a diagnostic harness, not a serial uploader.

## Toolchain references

The reproducible package tuple is the Ubuntu Noble extracted package set:

- GCC AVR 7.3.0, package `1:7.3.0+Atmel3.7.0-1`
- Binutils AVR 2.26.20160125, package `2.26.20160125+Atmel3.7.0-2`
- AVR-LibC 2.0.0, package `1:2.0.0+Atmel3.7.0-1`
- Native GCC 13.3.0

Version-matched official references used for the flags and reports:

- [GCC 7.3 AVR options](https://gcc.gnu.org/onlinedocs/gcc-7.3.0/gcc/AVR-Options.html)
- [GCC 7.3 overall options](https://gcc.gnu.org/onlinedocs/gcc-7.3.0/gcc/Overall-Options.html)
- [AVR-LibC 2.0.0 using tools](https://avrdudes.github.io/avr-libc/avr-libc-user-manual-2.0.0/using_tools.html)
- [AVR-LibC 2.0.0 memory sections](https://avrdudes.github.io/avr-libc/avr-libc-user-manual-2.0.0/mem_sections.html)
- [Binutils 2.26 objdump](https://sourceware.org/binutils/docs-2.26/binutils/objdump.html)
- [Binutils 2.26 size](https://sourceware.org/binutils/docs-2.26/binutils/size.html)
- [Binutils 2.26 linker options](https://sourceware.org/binutils/docs-2.26/ld/Options.html)

The AVR compiler tuple is compatible with the Arduino toolchain version family,
but this package does not copy Arduino or Freenove code and does not claim the
Arduino patch set.

## Limits and acceptance still required

The source and diagnostic image do not establish a physical safe posture,
power-cut guarantee, pin-map correctness, output reset behavior on the actual
PCB, watchdog qualification, actuator isolation, or rollback of the preserved
installed image. The board revision, output mapping, fuse/lock state, and
bootloader restoration limits remain outside this package. Do not flash,
connect actuator power, expose motion, or call this HIL or operational firmware.
Later acceptance must include measured output mapping, hardware watchdog
qualification, unpowered board tests, supported-bench tests, an independent
actuator cutoff, and a reviewed rollback procedure.
The epoch-exhaustion branch is source-reviewed but not dynamically exercised;
normal expiry, sequence/time wrap and fault interleavings are covered by tests.
