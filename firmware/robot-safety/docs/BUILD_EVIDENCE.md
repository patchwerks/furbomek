# Build evidence

Evidence date: 2026-10-15. All commands ran from the repository root on the
native host. No serial device, bootloader, controller, flash, EEPROM, fuse,
lock bit, or actuator was accessed.

## TDD red-first

Before implementation existed, this command was run:

```sh
g++ -std=c++17 -Wall -Wextra -Wpedantic -Werror \
  -I firmware/robot-safety/include \
  firmware/robot-safety/tests/test_main.cpp \
  firmware/robot-safety/tests/test_kernel.cpp \
  firmware/robot-safety/tests/test_frame.cpp \
  firmware/robot-safety/tests/test_integration.cpp \
  -o /tmp/opencode/robot-safety-red-test
```

Exit status: `1`, with the expected missing `robot_safety/frame.h` error.

After the focused regressions were added but before the ordering and shape
fixes, the implementation compiled but the test executable exited `1` with
`FAIL: deadline renewal cannot revive expired lease`. A separate pre-fix run
of the short-frame cases exited `1` with
`FAIL: short frame rejected at shape boundary`.

With the commit-fault tests present but before the commit guard checked the
fault signal inside its critical section, the executable exited `1` with
`FAIL: fault before commit cannot report accepted reply`.

## Native verification

```sh
firmware/robot-safety/check-safety.sh
```

Exit status: `0`. It found no actuator, vendor, EEPROM, watchdog, device,
heap, or host-library tokens in shared/AVR source.

```sh
firmware/robot-safety/test.sh
```

Exit status: `0`. Result: `robot-safety native tests: 93 checks passed`
with independent suite counts `kernel=44`, `frame=24`, and
`integration=25`. The tests cover boot latch, exact expiry, TTL 49/50/500/501
boundaries, millisecond wrap, sequence deltas 32767 and 32768, the
32767-to-65535-to-zero wrap path, duplicate/stale/rate rejection, interbyte
deadline expiry, priority STOP from leased/disarmed/latched states, emergency
STOP, idempotent epoch behavior, stale clear, known CRC vector, bad CRC,
partial timeout including timer wrap, short valid frames 1 through 7,
oversized input, unknown opcode, unknown version, embedded sync,
deterministic random bytes, parser/kernel integration, reply ordering,
telemetry backpressure, sticky transport fault, fault-before-commit rejection,
fault-after-commit acceptance followed by latching, and post-fault clear
rejection.

```sh
firmware/robot-safety/build.sh --native --output-dir /tmp/opencode/robot-safety-native-build
```

Exit status: `0`. This used native `g++ (Ubuntu 13.3.0-6ubuntu2~24.04.1)`.

```sh
AVR_ROOT=/tmp/opencode/furbomek-avr-toolchain \
  firmware/robot-safety/build.sh --all --output-dir /tmp/opencode/robot-safety-final-all
```

Exit status: `0`; the final combined native and AVR build matched the clean
AVR artifacts below.

Manual CLI paths, all exit status `0`:

```sh
/tmp/opencode/robot-safety-native-build/native/robot-safety-driver --help
printf 'clear\nlease 100 0\ntick 19\nlease 100 1\nstop\nstatus\nquit\n' | \
  /tmp/opencode/robot-safety-native-build/native/robot-safety-driver
```

The happy transcript began at `READY state=STOP_LATCHED epoch=0
capabilities=0`, accepted clear and lease, rejected the renewal at 19 ms as
`RATE_REJECTED`, then accepted priority STOP as `STOP_LATCHED epoch=2`.
The response showed `fault=0` and `capabilities=0` throughout.

```sh
printf 'clear\nbytes A5 5A 00\nlease 40 0\nfault\nclear\nquit\n' | \
  /tmp/opencode/robot-safety-native-build/native/robot-safety-driver
```

The negative transcript produced a `STATE_REJECTED` response for malformed
zero-length framing, rejected the 40 ms lease as `TTL_REJECTED`, latched
`FAULT sticky=1 state=STOP_LATCHED`, and emitted no clear response after the
sticky fault.

```sh
printf 'lease -1 0\nquit\n' | \
  /tmp/opencode/robot-safety-native-build/native/robot-safety-driver
```

This exits `0` and prints `ERR lease-argument`; signed numeric input is not
accepted by the driver.

## AVR verification

The toolchain was downloaded with `apt-get download` and extracted with
`dpkg-deb -x` into `/tmp/opencode/furbomek-avr-toolchain`; no system package
was installed. Confirmed versions:

```text
avr-g++ (GCC) 7.3.0
GNU ld (GNU Binutils) 2.26.20160125
GNU objdump (GNU Binutils) 2.26.20160125
GNU size (GNU Binutils) 2.26.20160125
avr-libc package 1:2.0.0+Atmel3.7.0-1
target -mmcu=atmega2560
```

Two clean builds used:

```sh
AVR_ROOT=/tmp/opencode/furbomek-avr-toolchain \
  firmware/robot-safety/build.sh --all --output-dir /tmp/opencode/robot-safety-final-a
AVR_ROOT=/tmp/opencode/furbomek-avr-toolchain \
  firmware/robot-safety/build.sh --avr --output-dir /tmp/opencode/robot-safety-final-b
```

Both exited `0`; `cmp` exited `0` for both ELF and HEX. The matching hashes
were:

```text
diagnostic.hex  e95f283f5983ab7b39beda5bbfc246b7b9e74d2cba09a6b0d99b7be37b58a951
diagnostic.elf  9f4d8f92b3c6c9b40eb98a73ac952ac73128ed3abbe63dff228c3b81b991671c
```

The AVR size report was `text=4020`, `data=80`, `bss=139`, `dec=4239`,
`hex=108f`. The undefined-symbol report was empty. The linker map records an
empty default `.eeprom` region of size `0`; the image has no EEPROM data section
or access routines. The standard `.note.gnu.avr.deviceinfo` metadata includes an
`__eeprom_end` symbol, not an EEPROM write operation. The objdump and map are
emitted for independent review.

The source scan and symbol report show no vendor library, actuator operation,
EEPROM call, watchdog enable, raw GPIO port operation, upload command, or
device path. The only AVR register families written by the shell are UART0,
Timer1, `MCUSR`, and interrupt-control registers. The image does not enable the
hardware watchdog; inherited bootloader watchdog state and reset behavior are
unqualified on hardware.
The emitted `diagnostic.timer-order.txt` passed the actual AVR disassembly
ordering check for timer stop, flag clear, compare setup, CTC mode, clock start,
and interrupt unmask.

## Non-claims

This evidence proves build and host simulation behavior only. It does not prove
physical safe posture, power removal, pin-map correctness, boot/reset output
inactivity on the actual controller, watchdog qualification, rollback, HIL,
or operational motion firmware. No flash command exists in this package and
no hardware operation was attempted.
