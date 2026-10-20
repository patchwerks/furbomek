#!/usr/bin/env bash
set -euo pipefail
repo=$(realpath "$(dirname "$0")/..")
if [[ ${1:-} == --help ]]; then
  printf '%s\n' 'Usage: bash tools/verify-media.sh' \
    'Run locked, non-live Python, snapshot and Godot media verification.' \
    'Set FURBOMEK_GODOT to an installed Godot 4.7 binary when needed.' \
    'Does not open devices, start OBS/Hermes/services, or install system tools.'
  exit 0
fi
[[ $# -eq 0 ]] || { printf '%s\n' 'Unexpected arguments; see --help.' >&2; exit 2; }
godot=${FURBOMEK_GODOT:-/data/furbomek-media/godot/godot}
command -v uv > /dev/null || { printf '%s\n' 'Missing prerequisite: uv' >&2; exit 2; }
[[ -x $godot ]] || { printf '%s\n' 'Missing prerequisite: set FURBOMEK_GODOT to Godot 4.7' >&2; exit 2; }
for name in embodiment-gateway hermes-activity stream-supervisor; do
  project=$repo/services/$name
  (
    pushd "$project" > /dev/null
    uv run --frozen pytest -q
    uv run --frozen ruff check .
    uv run --frozen ruff format --check .
    uv run --frozen basedpyright
    uv lock --check
    popd > /dev/null
  )
done
uv run --frozen --script "$repo/services/camera-capture/tests/test_snapshot.py"
bash -n "$repo/tools/kinect2/stream.sh" "$repo/tools/kinect2/launch-host.sh"
"$godot" --headless --path "$repo/tools/kinect2/godot" --check-only --script res://activity_fixture_runner.gd
"$godot" --headless --path "$repo/tools/kinect2/godot" --script res://activity_fixture_runner.gd
