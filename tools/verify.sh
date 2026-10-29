#!/usr/bin/env bash
# Non-live verification dispatcher. It does not install prerequisites.
set -uo pipefail
repo=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo" || exit 2

usage() {
  cat <<'EOF'
Usage: bash tools/verify.sh [COMPONENT ...]
No arguments runs every component; unavailable prerequisites are not passes.
  dispatcher    verification CLI regression tests (Python 3)
  media         unchanged locked Python/snapshot/Godot gate
  robot-native  actuator-disabled native safety tests and source scan
  guard-native  native guarded-firmware tests (requires pinned vendor inputs)
  robot-avr     diagnostic AVR build (requires AVR_ROOT)
  guard-avr     guarded AVR build (requires vendor inputs and AVR_ROOT)
  legacy        legacy Nuxt build (requires preinstalled locked dependencies)
Exit: 0 all selected checks pass; 1 any failure; 2 unavailable prerequisite/usage.
Run candidate code only in an isolated credential-free worker. This script is
not a sandbox. Never run it on a production/device host to qualify a PR.
EOF
}
if [[ ${1:-} == --help && $# -eq 1 ]]; then usage; exit 0; fi
if [[ $# -eq 0 ]]; then set -- dispatcher media robot-native guard-native robot-avr guard-avr legacy; fi
# Validate the whole selection before executing anything.
for component in "$@"; do
  case "$component" in
    dispatcher|media|robot-native|guard-native|robot-avr|guard-avr|legacy) ;;
    *) printf 'Unknown component: %s\n' "$component" >&2; usage >&2; exit 2 ;;
  esac
done

require_tool() { command -v "$1" >/dev/null || { printf 'Missing prerequisite: %s\n' "$1" >&2; return 125; }; }
require_file() { [[ -f $1 ]] || { printf 'Missing prerequisite: %s\n' "$1" >&2; return 125; }; }
require_vendor_inputs() {
  require_file "${FNHR_DIR:-/tmp/opencode/fnhr/FNHR}/src/FNHRBasic.cpp"
  require_file "${FREENOVE_ROOT:-/tmp/opencode/freenove-hermes}/ArduinoLibraries/FNHR.zip"
  require_file "${ARDUINO_CORE_DIR:-/tmp/opencode/ArduinoCore-avr-1.8.6}/cores/arduino/Arduino.h"
}
verify_component() (
  set -e
  case "$1" in
    dispatcher) require_tool python3; python3 tools/tests/test_verify.py ;;
    media)
      require_tool uv
      [[ -x ${FURBOMEK_GODOT:-/data/furbomek-media/godot/godot} ]] || {
        printf 'Missing prerequisite: FURBOMEK_GODOT executable (Godot 4.7)\n' >&2
        exit 125
      }
      bash tools/verify-media.sh ;;
    robot-native)
      require_tool "${CXX:-g++}"
      require_tool rg
      bash firmware/robot-safety/check-safety.sh
      bash firmware/robot-safety/test.sh ;;
    guard-native)
      require_tool "${CXX:-g++}"
      require_tool sha256sum
      require_vendor_inputs
      bash firmware/freenove-guard/test.sh ;;
    robot-avr|guard-avr)
      [[ -n ${AVR_ROOT:-} ]] || { printf 'Missing prerequisite: AVR_ROOT\n' >&2; exit 125; }
      [[ -x $AVR_ROOT/usr/bin/avr-g++ ]] || { printf 'Missing prerequisite: AVR_ROOT/usr/bin/avr-g++\n' >&2; exit 125; }
      require_tool sha256sum
      build_dir=$(mktemp -d "${TMPDIR:-/tmp}/furbomek-verify.XXXXXX")
      trap 'rm -rf "$build_dir"' EXIT
      if [[ $1 == robot-avr ]]; then package=robot-safety; else package=freenove-guard; require_vendor_inputs; fi
      bash "firmware/$package/build.sh" --avr --output-dir "$build_dir" ;;
    legacy)
      require_tool npm
      [[ -x node_modules/.bin/nuxt ]] || {
        printf 'Missing prerequisite: locked root/server npm dependencies; see docs/operations/repository-verification.md\n' >&2
        exit 125
      }
      npm run build ;;
  esac
)

failed=0
unavailable=0
for component in "$@"; do
  printf '\nRUN %s\n' "$component"
  # Do not call the function in an if/|| context: that disables errexit inside
  # its subshell and could turn an earlier failed check into a successful result.
  verify_component "$component"
  result=$?
  case "$result" in
    0) printf 'PASS %s\n' "$component" ;;
    125) printf 'UNAVAILABLE %s (prerequisite)\n' "$component"; unavailable=$((unavailable + 1)) ;;
    *) printf 'FAIL %s (exit %s)\n' "$component" "$result"; failed=$((failed + 1)) ;;
  esac
done
printf '\nSummary: %s failed; %s unavailable.\n' "$failed" "$unavailable"
if (( failed > 0 )); then exit 1; fi
if (( unavailable > 0 )); then exit 2; fi
