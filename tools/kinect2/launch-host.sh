#!/usr/bin/env bash
set -euo pipefail
repo=$(realpath "$(dirname "$0")/../..")
media=${FURBOMEK_MEDIA_ROOT:-/data/furbomek-media}
export FURBOMEK_MEDIA_ROOT="$media"
export DISPLAY=${DISPLAY:-:1}
export XAUTHORITY=${XAUTHORITY:-/run/user/$(id -u)/gdm/Xauthority}
export FURBOMEK_KINECT_DIR=${FURBOMEK_KINECT_DIR:-/dev/shm/furbomek-kinect2-$(id -u)}
export XDG_CONFIG_HOME="$media/obs-config"
export QT_QPA_PLATFORM=xcb
if [[ ${1:-} == --help ]]; then
  printf '%s\n' 'Usage: bash tools/kinect2/launch-host.sh [--record]' \
    'Launch host Kinect capture, Godot point cloud and isolated OBS Kinect2 profile.' \
    'No public stream starts. In OBS, F10 stops recording; configure your own stream destination.'
  exit 0
fi
if [[ $# -gt 1 || ( $# -eq 1 && ${1:-} != --record ) ]]; then
  printf '%s\n' 'Only --record or --help is accepted.' >&2
  exit 2
fi
for executable in "$media/capture-build/furbomek-kinect2" "$media/godot/godot"; do
  [[ -x $executable ]] || { printf 'Missing %s; run build-host.sh first.\n' "$executable" >&2; exit 1; }
done
exec uv run --frozen --project "$repo/services/stream-supervisor" \
  python "$repo/services/stream-supervisor/supervisor.py" "$@"
