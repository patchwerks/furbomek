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
mkdir -p "$media/logs" "$media/recordings"
exec 9>"$media/host-session.lock"
flock -n 9 || { printf '%s\n' 'The host Kinect session is already running.' >&2; exit 1; }
capture_pid=''
viewer_pid=''
tracker_pid=''
cleanup() {
  if [[ -n $capture_pid ]]; then kill -TERM "$capture_pid" 2>/dev/null || true; fi
  if [[ -n $viewer_pid ]]; then kill -TERM "$viewer_pid" 2>/dev/null || true; fi
  if [[ -n $tracker_pid ]]; then kill -TERM "$tracker_pid" 2>/dev/null || true; fi
  wait 2>/dev/null || true
}
trap cleanup EXIT
"$media/capture-build/furbomek-kinect2" >"$media/logs/capture.log" 2>&1 &
capture_pid=$!
uv run --no-project --python /usr/bin/python3.12 "$repo/services/camera-capture/track.py" >"$media/logs/tracking.log" 2>&1 &
tracker_pid=$!
"$media/godot/godot" --path "$repo/tools/kinect2/godot" >"$media/logs/godot.log" 2>&1 &
viewer_pid=$!
ready=false
for ((attempt=0; attempt<30; attempt++)); do
  kill -0 "$capture_pid" 2>/dev/null || { printf '%s\n' 'Capture failed; see capture.log.' >&2; exit 1; }
  kill -0 "$viewer_pid" 2>/dev/null || { printf '%s\n' 'Viewer failed; see godot.log.' >&2; exit 1; }
  kill -0 "$tracker_pid" 2>/dev/null || { printf '%s\n' 'Tracker failed; see tracking.log.' >&2; exit 1; }
  if [[ -s $FURBOMEK_KINECT_DIR/tracking.json ]] && \
      node "$repo/tools/kinect2/configure-obs.mjs" 2>"$media/logs/obs-configure.log"; then
    ready=true
    break
  fi
  sleep 1
done
[[ $ready == true ]] || { printf '%s\n' 'Timed out waiting for capture/viewer.' >&2; exit 1; }
args=(--multi --profile Kinect2 --collection Kinect2 --disable-missing-files-check)
if [[ ${1:-} == --record ]]; then args+=(--startrecording); fi
printf '%s\n' 'Kinect2 + Godot + OBS running. Close OBS to end this host session.'
obs "${args[@]}" >"$media/logs/obs-launch.log" 2>&1
