#!/usr/bin/env bash
set -euo pipefail

root_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
mode=all
output_dir=
avr_root=${AVR_ROOT:-}
fnhr_dir=${FNHR_DIR:-/tmp/opencode/fnhr/FNHR}
core_dir=${ARDUINO_CORE_DIR:-/tmp/opencode/ArduinoCore-avr-1.8.6}
vendor_root=${FREENOVE_ROOT:-/tmp/opencode/freenove-hermes}

usage() {
  printf '%s\n' \
    'usage: build.sh [--native|--avr|--all] [--output-dir DIR] [--avr-root DIR]' \
    'inputs default to the pinned offline paths under /tmp/opencode' \
    'the script never downloads, installs, flashes, or opens a serial device'
}

while (($# > 0)); do
  case "$1" in
    --native) mode=native ;;
    --avr) mode=avr ;;
    --all) mode=all ;;
    --output-dir) shift; (($# > 0)) || { usage >&2; exit 2; }; output_dir=$1 ;;
    --avr-root) shift; (($# > 0)) || { usage >&2; exit 2; }; avr_root=$1 ;;
    --help) usage; exit 0 ;;
    *) usage >&2; exit 2 ;;
  esac
  shift
done

if [[ -z "$output_dir" ]]; then output_dir=$(mktemp -d "${TMPDIR:-/tmp}/freenove-guard-build.XXXXXX"); else mkdir -p "$output_dir"; fi

require_file() { [[ -f "$1" ]] || { printf 'missing: %s\n' "$1" >&2; exit 2; }; }
require_tool() { command -v "$1" >/dev/null || { printf 'missing tool: %s\n' "$1" >&2; exit 2; }; }
check_sha() {
  local file=$1 expected=$2 actual
  actual=$(sha256sum "$file" | cut -d' ' -f1)
  [[ "$actual" == "$expected" ]] || { printf 'hash mismatch: %s\n' "$file" >&2; exit 2; }
  printf '%s  %s\n' "$actual" "$file"
}

require_tool g++
require_tool sha256sum
require_tool unzip
require_tool patch
require_file "$fnhr_dir/src/FNHRBasic.cpp"
require_file "$fnhr_dir/src/FNHRBasic.h"
require_file "$fnhr_dir/src/FNHRRemote.cpp"
require_file "$fnhr_dir/src/FNHRRemote.h"
require_file "$fnhr_dir/LICENSE.txt"
require_file "$vendor_root/ArduinoLibraries/FNHR.zip"
require_file "$vendor_root/ArduinoLibraries/Servo.zip"
require_file "$vendor_root/ArduinoLibraries/FlexiTimer2.zip"
require_file "$vendor_root/ArduinoLibraries/RF24.zip"
require_file "$core_dir/cores/arduino/Arduino.h"

check_sha "$fnhr_dir/src/FNHRBasic.cpp" b3645b673d3ed0643b5600d32278a2c5afc38166ef58b0b3d4bc006ffb85465a > "$output_dir/preimage-sha256.txt"
check_sha "$fnhr_dir/src/FNHRBasic.h" 81bfad4a81ef9ee10b2e5a9edfdcfc08cdae217f00c1512e5aa1d97d97085403 >> "$output_dir/preimage-sha256.txt"
check_sha "$fnhr_dir/src/FNHRRemote.cpp" 869d22dd3b9dd39b3f997286051d29d0fe1c3878815440814b0d81057c737fbd >> "$output_dir/preimage-sha256.txt"
check_sha "$fnhr_dir/src/FNHRRemote.h" 0aecead6727add27b9d779585770874f712b4ce0ea1f31c130da12132ad82a3d >> "$output_dir/preimage-sha256.txt"
check_sha "$fnhr_dir/LICENSE.txt" 4645d812490670438f53d5cb541ee53248dbb9a228b9062df45aaf22f09734ad >> "$output_dir/preimage-sha256.txt"
check_sha "$vendor_root/ArduinoLibraries/FNHR.zip" dccc37b9707a705f097096cd66a02253b5ae3f6b7a7a77f6ba14b53a665f0d4b >> "$output_dir/preimage-sha256.txt"
check_sha "$vendor_root/ArduinoLibraries/Servo.zip" 27b4417e51c9a7193ea39afd763074f702f57b37fdd8181c95e6b4c01123ee04 >> "$output_dir/preimage-sha256.txt"
check_sha "$vendor_root/ArduinoLibraries/FlexiTimer2.zip" 02b8d3f3a99c6227994ca8df484ad38841e0027828ed176a24fea05e0333d230 >> "$output_dir/preimage-sha256.txt"
check_sha "$vendor_root/ArduinoLibraries/RF24.zip" 9d07cbbebebf413fd16dc2886e0365c3800002cbb01b0a888dcce41c1c5597de >> "$output_dir/preimage-sha256.txt"

if [[ -d "$core_dir/.git" ]]; then
  [[ "$(GIT_MASTER=1 git -C "$core_dir" rev-parse HEAD)" == 42fa4a1ea1b1b11d1cc0a60298e529d37f9d14bd ]] || exit 2
  [[ -z "$(GIT_MASTER=1 git -C "$core_dir" status --porcelain --untracked-files=all)" ]] || {
    printf 'ArduinoCore-avr worktree is dirty\n' >&2
    exit 2
  }
else
  printf 'ArduinoCore-avr git metadata missing\n' >&2
  exit 2
fi

native_cxx=${CXX:-g++}
native_flags=(-std=c++17 -Wall -Wextra -Wpedantic -Werror -Wshadow -Wconversion
  -ffile-prefix-map="$root_dir"=. -fdebug-prefix-map="$root_dir"=.
  -I "$root_dir/include")

build_native() {
  local native_dir="$output_dir/native"
  mkdir -p "$native_dir"
  "$native_cxx" "${native_flags[@]}" "$root_dir/src/frame.cpp" "$root_dir/src/frame_decode.cpp" "$root_dir/src/guard.cpp" "$root_dir/src/rf_link.cpp" \
    "$root_dir/src/manual.cpp" "$root_dir/src/dispatcher.cpp" "$root_dir/src/scheduler.cpp" "$root_dir/src/esp_diag.cpp" "$root_dir/src/metadata.cpp" \
    "$root_dir/tests/test_guard.cpp" -o "$native_dir/freenove-guard-tests"
  "$native_cxx" "${native_flags[@]}" "$root_dir/src/frame.cpp" "$root_dir/src/frame_decode.cpp" "$root_dir/src/guard.cpp" "$root_dir/src/rf_link.cpp" \
    "$root_dir/src/manual.cpp" "$root_dir/src/dispatcher.cpp" "$root_dir/src/scheduler.cpp" "$root_dir/src/esp_diag.cpp" "$root_dir/src/metadata.cpp" \
    "$root_dir/tools/driver.cpp" -o "$native_dir/freenove-guard-driver"
  "$native_dir/freenove-guard-tests"
  "$native_cxx" --version > "$native_dir/compiler-version.txt"
}

build_avr() {
  [[ -n "$avr_root" ]] || { printf 'AVR_ROOT is required for --avr\n' >&2; exit 2; }
  local avr_bin="$avr_root/usr/bin"
  local avr_cxx="$avr_bin/avr-g++"
  local avr_cc="$avr_bin/avr-gcc"
  local avr_objcopy="$avr_bin/avr-objcopy"
  local avr_objdump="$avr_bin/avr-objdump"
  local avr_size="$avr_bin/avr-size"
  local avr_nm="$avr_bin/avr-nm"
  local avr_strip="$avr_bin/avr-strip"
  local avr_readelf="$avr_bin/avr-readelf"
  for tool in "$avr_cxx" "$avr_cc" "$avr_objcopy" "$avr_objdump" "$avr_size" "$avr_nm" "$avr_strip" "$avr_readelf"; do
    [[ -x "$tool" ]] || { printf 'missing AVR tool: %s\n' "$tool" >&2; exit 2; }
  done
  [[ "$($avr_cxx --version | head -n1)" == 'avr-g++ (GCC) 7.3.0' ]] || exit 2
  [[ "$($avr_bin/avr-ld --version | head -n1)" == 'GNU ld (GNU Binutils) 2.26.20160125' ]] || exit 2

  local avr_dir="$output_dir/avr"
  local tree="$avr_dir/tree"
  local obj="$avr_dir/obj"
  local deps="$tree/deps"
  rm -rf "$tree"
  mkdir -p "$obj" "$deps/FNHR/src"
  cp "$fnhr_dir/src/FNHRBasic.cpp" "$deps/FNHR/src/FNHRBasic.cpp"
  cp "$fnhr_dir/src/FNHRBasic.h" "$deps/FNHR/src/FNHRBasic.h"
  sed -i 's/\r$//' "$deps/FNHR/src/FNHRBasic.cpp" "$deps/FNHR/src/FNHRBasic.h"
  unzip -oq "$vendor_root/ArduinoLibraries/Servo.zip" -d "$deps"
  unzip -oq "$vendor_root/ArduinoLibraries/FlexiTimer2.zip" -d "$deps"
  unzip -oq "$vendor_root/ArduinoLibraries/RF24.zip" -d "$deps"
  sed -i 's/\r$//' "$deps/Servo/src/avr/ServoTimers.h"
  patch --batch --fuzz=1 -l "$deps/FNHR/src/FNHRBasic.cpp" < "$root_dir/patches/FNHRBasic-no-eeprom-writes.patch" > "$avr_dir/patch.log"
  patch --batch --fuzz=1 -l "$deps/FNHR/src/FNHRBasic.cpp" < "$root_dir/patches/FNHRBasic.patch" >> "$avr_dir/patch.log"
  patch --batch --fuzz=1 -l "$deps/FNHR/src/FNHRBasic.h" < "$root_dir/patches/FNHRBasic.h.patch" >> "$avr_dir/patch.log"
  patch --batch --fuzz=1 -l "$deps/Servo/src/avr/ServoTimers.h" < "$root_dir/patches/ServoTimers.patch" >> "$avr_dir/patch.log"
  ! grep -q 'FAILED' "$avr_dir/patch.log"
  ! grep -q 'A13' "$deps/FNHR/src/FNHRBasic.h"
  ! grep -q 'EEPROM.write' "$deps/FNHR/src/FNHRBasic.cpp"
  ! grep -q 'digitalWrite' "$deps/FNHR/src/FNHRBasic.cpp"
  ! grep -q '_useTimer4' "$deps/Servo/src/avr/ServoTimers.h"

  local vendor_flags=(-mmcu=atmega2560 -DF_CPU=16000000UL -DARDUINO=10806 -DARDUINO_AVR_MEGA2560
    -DARDUINO_ARCH_AVR -std=c++11 -Os -ffreestanding -fno-exceptions -fno-rtti
    -fno-threadsafe-statics -fno-ident -ffunction-sections -fdata-sections -g0 -w
    -I "$core_dir/cores/arduino" -I "$core_dir/variants/mega"
    -I "$core_dir/libraries/EEPROM/src" -I "$deps/Servo/src" -I "$deps/Servo/src/avr"
    -I "$core_dir/libraries/SPI/src" -I "$deps/FlexiTimer2" -I "$deps/RF24" -I "$deps/FNHR/src" -I "$root_dir/include")
  local guard_flags=(-mmcu=atmega2560 -DF_CPU=16000000UL -DARDUINO=10806 -DARDUINO_AVR_MEGA2560
    -DARDUINO_ARCH_AVR -std=c++11 -Os -ffreestanding -fno-exceptions -fno-rtti
    -fno-threadsafe-statics -fno-ident -ffunction-sections -fdata-sections -g0
    -Wall -Wextra -Wshadow -Wconversion -Werror
    -I "$core_dir/cores/arduino" -I "$core_dir/variants/mega"
    -I "$core_dir/libraries/EEPROM/src" -I "$deps/Servo/src" -I "$deps/Servo/src/avr"
    -I "$core_dir/libraries/SPI/src" -I "$deps/FlexiTimer2" -I "$deps/RF24" -I "$deps/FNHR/src" -I "$root_dir/include")
  local shell_flags=(-mmcu=atmega2560 -DF_CPU=16000000UL -DARDUINO=10806 -DARDUINO_AVR_MEGA2560
    -DARDUINO_ARCH_AVR -std=c++11 -Os -ffreestanding -fno-exceptions -fno-rtti
    -fno-threadsafe-statics -fno-ident -ffunction-sections -fdata-sections -g0
    -Wall -Wextra -Wshadow -Wconversion -w
    -I "$core_dir/cores/arduino" -I "$core_dir/variants/mega"
    -I "$core_dir/libraries/EEPROM/src" -I "$deps/Servo/src" -I "$deps/Servo/src/avr"
    -I "$core_dir/libraries/SPI/src" -I "$deps/FlexiTimer2" -I "$deps/RF24" -I "$deps/FNHR/src" -I "$root_dir/include")
  local sources=(
    "$root_dir/src/frame.cpp" "$root_dir/src/frame_decode.cpp" "$root_dir/src/guard.cpp" "$root_dir/src/rf_link.cpp" "$root_dir/src/manual.cpp" "$root_dir/src/dispatcher.cpp" "$root_dir/src/scheduler.cpp" "$root_dir/src/esp_diag.cpp" "$root_dir/src/metadata.cpp"
    "$root_dir/avr/guard_main.cpp" "$root_dir/avr/guard_runtime.cpp" "$root_dir/avr/guard_service.cpp"
    "$deps/FNHR/src/FNHRBasic.cpp" "$deps/Servo/src/avr/Servo.cpp" "$deps/FlexiTimer2/FlexiTimer2.cpp"
    "$deps/RF24/RF24.cpp" "$core_dir/libraries/SPI/src/SPI.cpp"
    "$core_dir/cores/arduino/HardwareSerial.cpp" "$core_dir/cores/arduino/HardwareSerial0.cpp"
    "$core_dir/cores/arduino/HardwareSerial1.cpp" "$core_dir/cores/arduino/HardwareSerial2.cpp"
    "$core_dir/cores/arduino/HardwareSerial3.cpp" "$core_dir/cores/arduino/Print.cpp"
    "$core_dir/cores/arduino/Stream.cpp" "$core_dir/cores/arduino/WString.cpp"
    "$core_dir/cores/arduino/WMath.cpp" "$core_dir/cores/arduino/abi.cpp" "$core_dir/cores/arduino/new.cpp"
    "$core_dir/cores/arduino/hooks.c" "$core_dir/cores/arduino/wiring.c"
    "$core_dir/cores/arduino/wiring_analog.c" "$core_dir/cores/arduino/wiring_digital.c"
    "$core_dir/cores/arduino/wiring_pulse.c" "$core_dir/cores/arduino/wiring_pulse.S"
    "$core_dir/cores/arduino/wiring_shift.c" "$core_dir/cores/arduino/WInterrupts.c"
    "$core_dir/cores/arduino/main.cpp")
  local source base flags
  for source in "${sources[@]}"; do
    base=$(basename "$source")
    flags=("${vendor_flags[@]}")
    case "$source" in
      "$root_dir/src/"*) flags=("${guard_flags[@]}") ;;
      "$root_dir/avr/"*) flags=("${shell_flags[@]}") ;;
    esac
    case "$source" in
      *.c) "$avr_cc" "${flags[@]}" -c "$source" -o "$obj/$base.o" ;;
      *.S) "$avr_cc" "${flags[@]}" -c "$source" -o "$obj/$base.o" ;;
      *) "$avr_cxx" "${flags[@]}" -c "$source" -o "$obj/$base.o" ;;
    esac
  done
  "$avr_cxx" -mmcu=atmega2560 -Os -g0 -fno-exceptions -fno-rtti -fno-threadsafe-statics -fno-ident \
    -Wl,--build-id=none -Wl,--gc-sections -Wl,-Map="$avr_dir/guard.map" \
    "$obj"/*.o -o "$avr_dir/guard.elf"
  "$avr_strip" --strip-debug "$avr_dir/guard.elf"
  "$avr_objcopy" -O ihex -R .eeprom "$avr_dir/guard.elf" "$avr_dir/guard.hex"
  "$avr_objcopy" -O binary -j .text -j .data "$avr_dir/guard.elf" "$avr_dir/guard.flash.bin"
  "$avr_objdump" -h -S -t -x "$avr_dir/guard.elf" > "$avr_dir/guard.objdump.txt"
  "$avr_size" --format=Berkeley "$avr_dir/guard.elf" > "$avr_dir/guard.size.txt"
  "$avr_nm" -C --undefined-only "$avr_dir/guard.elf" > "$avr_dir/guard.undefined.txt"
  {
    printf 'TIMER4_COMPA_vect=__vector_42 source=avr/guard_main.cpp\n'
    "$avr_nm" -C "$avr_dir/guard.elf" | grep -E '__vector_42$'
  } > "$avr_dir/guard.vectors.txt"
  "$root_dir/tools/check-avr-policy.sh" "$root_dir/avr/guard_main.cpp" "$root_dir/avr/guard_runtime.cpp" \
    "$avr_dir/guard.objdump.txt" "$avr_dir/guard.vectors.txt" > "$avr_dir/guard.policy.txt"
  [[ ! -s "$avr_dir/guard.undefined.txt" ]]
  ! grep -q '\.eeprom' "$avr_dir/guard.objdump.txt"
  [[ $(stat -c '%s' "$avr_dir/guard.flash.bin") -lt 253952 ]]
  [[ $(grep -c 'TIMER4_COMPA_vect' "$root_dir/avr/guard_main.cpp") -eq 1 ]]
  sha256sum "$avr_dir/guard.hex" "$avr_dir/guard.elf" > "$avr_dir/guard.sha256"
  "$avr_cxx" --version > "$avr_dir/tool-versions.txt"
  "$avr_bin/avr-ld" --version >> "$avr_dir/tool-versions.txt"
  "$avr_size" --version >> "$avr_dir/tool-versions.txt"
}

build_remote() {
  [[ -n "$avr_root" ]] || { printf 'AVR_ROOT is required for remote build\n' >&2; exit 2; }
  local avr_bin="$avr_root/usr/bin"
  local avr_cxx="$avr_bin/avr-g++"
  local avr_cc="$avr_bin/avr-gcc"
  local avr_objcopy="$avr_bin/avr-objcopy"
  local avr_size="$avr_bin/avr-size"
  local avr_nm="$avr_bin/avr-nm"
  local avr_strip="$avr_bin/avr-strip"
  for tool in "$avr_cxx" "$avr_cc" "$avr_objcopy" "$avr_size" "$avr_nm" "$avr_strip"; do
    [[ -x "$tool" ]] || { printf 'missing AVR tool: %s\n' "$tool" >&2; exit 2; }
  done
  local remote_dir="$output_dir/remote"
  local tree="$remote_dir/tree"
  local obj="$remote_dir/obj"
  local deps="$tree/deps"
  rm -rf "$tree"
  mkdir -p "$obj" "$deps/FNHR/src"
  cp "$fnhr_dir/src/FNHRRemote.cpp" "$deps/FNHR/src/FNHRRemote.cpp"
  cp "$fnhr_dir/src/FNHRRemote.h" "$deps/FNHR/src/FNHRRemote.h"
  cp "$fnhr_dir/src/FNHROrders.h" "$deps/FNHR/src/FNHROrders.h"
  sed -i 's/\r$//' "$deps/FNHR/src/FNHRRemote.cpp" "$deps/FNHR/src/FNHRRemote.h" "$deps/FNHR/src/FNHROrders.h"
  unzip -oq "$vendor_root/ArduinoLibraries/RF24.zip" -d "$deps"
  patch --batch --fuzz=3 -l "$deps/FNHR/src/FNHRRemote.h" < "$root_dir/patches/FNHRRemote.h.patch" > "$remote_dir/patch.log"
  patch --batch --fuzz=3 -l "$deps/FNHR/src/FNHRRemote.cpp" < "$root_dir/patches/FNHRRemote.cpp.patch" >> "$remote_dir/patch.log"
  ! grep -q 'FAILED' "$remote_dir/patch.log"
  local flags=(-mmcu=atmega328p -DF_CPU=16000000UL -DARDUINO=10806 -DARDUINO_AVR_UNO
    -DARDUINO_ARCH_AVR -std=c++11 -Os -ffreestanding -fno-exceptions -fno-rtti
    -fno-threadsafe-statics -fno-ident -ffunction-sections -fdata-sections -g0 -w
    -I "$core_dir/cores/arduino" -I "$core_dir/variants/standard" -I "$core_dir/libraries/SPI/src"
    -I "$deps/RF24" -I "$deps/FNHR/src" -I "$root_dir/include")
  local source base
  local sources=(
    "$root_dir/src/frame.cpp" "$root_dir/src/frame_decode.cpp" "$root_dir/src/guard.cpp" "$root_dir/src/rf_link.cpp" "$root_dir/src/manual.cpp" "$root_dir/src/dispatcher.cpp" "$root_dir/src/scheduler.cpp" "$root_dir/src/esp_diag.cpp" "$root_dir/src/metadata.cpp"
    "$root_dir/avr/remote_main.cpp"
    "$deps/FNHR/src/FNHRRemote.cpp" "$deps/RF24/RF24.cpp" "$core_dir/libraries/SPI/src/SPI.cpp"
    "$core_dir/cores/arduino/HardwareSerial.cpp" "$core_dir/cores/arduino/HardwareSerial0.cpp"
    "$core_dir/cores/arduino/Print.cpp" "$core_dir/cores/arduino/Stream.cpp"
    "$core_dir/cores/arduino/WString.cpp" "$core_dir/cores/arduino/WMath.cpp"
    "$core_dir/cores/arduino/abi.cpp" "$core_dir/cores/arduino/new.cpp"
    "$core_dir/cores/arduino/hooks.c" "$core_dir/cores/arduino/wiring.c"
    "$core_dir/cores/arduino/wiring_analog.c" "$core_dir/cores/arduino/wiring_digital.c"
    "$core_dir/cores/arduino/wiring_pulse.c" "$core_dir/cores/arduino/wiring_pulse.S"
    "$core_dir/cores/arduino/wiring_shift.c" "$core_dir/cores/arduino/WInterrupts.c"
    "$core_dir/cores/arduino/main.cpp")
  for source in "${sources[@]}"; do
    base=$(basename "$source")
    case "$source" in
      *.c|*.S) "$avr_cc" "${flags[@]}" -c "$source" -o "$obj/$base.o" ;;
      *) "$avr_cxx" "${flags[@]}" -c "$source" -o "$obj/$base.o" ;;
    esac
  done
  "$avr_cxx" -mmcu=atmega328p -Os -g0 -fno-exceptions -fno-rtti -fno-threadsafe-statics -fno-ident \
    -Wl,--build-id=none -Wl,--gc-sections -Wl,-Map="$remote_dir/remote.map" \
    "$obj"/*.o -o "$remote_dir/remote.elf"
  "$avr_strip" --strip-debug "$remote_dir/remote.elf"
  "$avr_objcopy" -O ihex -R .eeprom "$remote_dir/remote.elf" "$remote_dir/remote.hex"
  "$avr_objcopy" -O binary -j .text -j .data "$remote_dir/remote.elf" "$remote_dir/remote.flash.bin"
  "$avr_size" --format=Berkeley "$remote_dir/remote.elf" > "$remote_dir/remote.size.txt"
  "$avr_nm" -C --undefined-only "$remote_dir/remote.elf" > "$remote_dir/remote.undefined.txt"
  [[ ! -s "$remote_dir/remote.undefined.txt" ]]
  [[ $(stat -c '%s' "$remote_dir/remote.flash.bin") -lt 30720 ]]
  sha256sum "$remote_dir/remote.hex" "$remote_dir/remote.elf" > "$remote_dir/remote.sha256"
}

if [[ "$mode" == native || "$mode" == all ]]; then build_native; fi
if [[ "$mode" == avr || "$mode" == all ]]; then build_avr; build_remote; fi
printf 'build output: %s\n' "$output_dir"
