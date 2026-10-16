#!/usr/bin/env bash
set -euo pipefail

root_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
mode=all
output_dir=
avr_root=${AVR_ROOT:-${AVR_TOOLCHAIN:-}}

usage() {
  printf '%s\n' \
    'usage: build.sh [--native|--avr|--all] [--output-dir DIR] [--avr-root DIR]' \
    'default output is a temporary directory outside the source tree' \
    'AVR_ROOT or --avr-root must point to an extracted AVR toolchain; no download is performed'
}

while (($# > 0)); do
  case "$1" in
    --native) mode=native ;;
    --avr) mode=avr ;;
    --all) mode=all ;;
    --output-dir)
      shift
      (($# > 0)) || { usage >&2; exit 2; }
      output_dir=$1
      ;;
    --avr-root)
      shift
      (($# > 0)) || { usage >&2; exit 2; }
      avr_root=$1
      ;;
    --help)
      usage
      exit 0
      ;;
    *)
      usage >&2
      exit 2
      ;;
  esac
  shift
done

if [[ -z "$output_dir" ]]; then
  output_dir=$(mktemp -d "${TMPDIR:-/tmp}/robot-safety-build.XXXXXX")
else
  mkdir -p "$output_dir"
fi

native_cxx=${CXX:-g++}
common_sources=(
  "$root_dir/src/safety_kernel.cpp"
  "$root_dir/src/frame.cpp"
  "$root_dir/src/protocol.cpp"
)
native_flags=(
  -std=c++17 -Wall -Wextra -Wpedantic -Werror -Wshadow -Wconversion
  -ffile-prefix-map="$root_dir"=. -fdebug-prefix-map="$root_dir"=.
  -I "$root_dir/include"
)

build_native() {
  local native_dir="$output_dir/native"
  mkdir -p "$native_dir"
  "$native_cxx" "${native_flags[@]}" "${common_sources[@]}" \
    "$root_dir/tests/test_main.cpp" "$root_dir/tests/test_kernel.cpp" \
    "$root_dir/tests/test_frame.cpp" "$root_dir/tests/test_integration.cpp" \
    -o "$native_dir/robot-safety-tests"
  "$native_cxx" "${native_flags[@]}" "${common_sources[@]}" \
    "$root_dir/tools/driver.cpp" -o "$native_dir/robot-safety-driver"
  "$native_cxx" --version > "$native_dir/compiler-version.txt"
}

build_avr() {
  [[ -n "$avr_root" ]] || { printf '%s\n' 'AVR_ROOT is required for --avr' >&2; exit 2; }
  local avr_bin="$avr_root/usr/bin"
  local avr_cxx="$avr_bin/avr-g++"
  local avr_objcopy="$avr_bin/avr-objcopy"
  local avr_objdump="$avr_bin/avr-objdump"
  local avr_size="$avr_bin/avr-size"
  local avr_nm="$avr_bin/avr-nm"
  local avr_strip="$avr_bin/avr-strip"
  [[ -x "$avr_cxx" && -x "$avr_objcopy" && -x "$avr_objdump" && -x "$avr_size" && -x "$avr_nm" && -x "$avr_strip" ]] || {
    printf '%s\n' "missing extracted AVR tools under $avr_bin" >&2
    exit 2
  }
  local avr_dir="$output_dir/avr"
  local obj_dir="$avr_dir/obj"
  mkdir -p "$obj_dir"
  local avr_flags=(
    -mmcu=atmega2560 -std=c++11 -Os -ffreestanding -fno-exceptions -fno-rtti
    -fno-threadsafe-statics -Wall -Wextra -Wpedantic -Wshadow -Wconversion -Werror
    -ffunction-sections -fdata-sections -fno-ident -g0 -I "$root_dir/include"
  )
  local source
  for source in safety_kernel frame protocol; do
    "$avr_cxx" "${avr_flags[@]}" -c "$root_dir/src/$source.cpp" -o "$obj_dir/$source.o"
  done
  "$avr_cxx" "${avr_flags[@]}" -DF_CPU=16000000UL -c "$root_dir/avr/diagnostic_main.cpp" \
    -o "$obj_dir/diagnostic_main.o"
  "$avr_cxx" -mmcu=atmega2560 -Os -g0 -fno-exceptions -fno-rtti -fno-threadsafe-statics -fno-ident \
    -Wl,--build-id=none -Wl,--gc-sections -Wl,-Map="$avr_dir/diagnostic.map" \
    "$obj_dir/safety_kernel.o" "$obj_dir/frame.o" "$obj_dir/protocol.o" "$obj_dir/diagnostic_main.o" \
    -o "$avr_dir/diagnostic.elf"
  "$avr_strip" --strip-debug "$avr_dir/diagnostic.elf"
  "$avr_objcopy" -O ihex -R .eeprom "$avr_dir/diagnostic.elf" "$avr_dir/diagnostic.hex"
  "$avr_objdump" -h -S -t -x "$avr_dir/diagnostic.elf" > "$avr_dir/diagnostic.objdump.txt"
  "$root_dir/tools/check-avr-timer-order.sh" "$avr_dir/diagnostic.objdump.txt" > "$avr_dir/diagnostic.timer-order.txt"
  "$avr_size" --format=Berkeley "$avr_dir/diagnostic.elf" > "$avr_dir/diagnostic.size.txt"
  "$avr_nm" -C --undefined-only "$avr_dir/diagnostic.elf" > "$avr_dir/diagnostic.undefined.txt"
  sha256sum "$avr_dir/diagnostic.hex" "$avr_dir/diagnostic.elf" > "$avr_dir/diagnostic.sha256"
  {
    "$avr_cxx" --version
    "$avr_bin/avr-ld" --version
    "$avr_objdump" --version
    "$avr_size" --version
    "$avr_root/usr/bin/avr-gcc" -print-file-name=libc.a
  } > "$avr_dir/tool-versions.txt"
}

if [[ "$mode" == native || "$mode" == all ]]; then
  build_native
fi
if [[ "$mode" == avr || "$mode" == all ]]; then
  build_avr
fi
printf 'build output: %s\n' "$output_dir"
