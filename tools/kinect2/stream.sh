#!/usr/bin/env bash
set -euo pipefail

unit=furbomek-stream.service
media=${FURBOMEK_MEDIA_ROOT:-/data/furbomek-media}
runtime=${XDG_RUNTIME_DIR:-/run/user/$(id -u)}
state_dir=$runtime/furbomek-stream
settings=$state_dir/settings.json

usage() {
  printf '%s\n' \
    'Usage: bash tools/kinect2/stream.sh {start [options]|stop|status|restart [options]|logs}' \
    'Options: --record --screen-policy off|bot-desktop --readiness-timeout-s 1..300' \
    'Private Kinect capture, tracking, activity broker, Godot viewer and OBS session.' \
    'Default screen policy is off; no public stream is started.'
}

reject_args() {
  [[ $# -eq 0 ]] || { printf '%s\n' 'Unexpected arguments.' >&2; exit 2; }
}

write_settings() {
  local record=$1
  local screen_policy=$2
  local readiness_timeout_s=$3
  local temporary
  umask 077
  mkdir -p "$state_dir"
  chmod 700 "$state_dir"
  temporary=$(mktemp "$state_dir/.settings.XXXXXX")
  printf '{"schema_version":1,"record":%s,"screen_policy":"%s","readiness_timeout_s":%s}\n' \
    "$record" "$screen_policy" "$readiness_timeout_s" >"$temporary"
  chmod 600 "$temporary"
  mv -f "$temporary" "$settings"
}

read_existing_settings() {
  python3 - "$settings" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
try:
    document = json.loads(path.read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError):
    document = {}
record = "true" if document.get("record") is True else "false"
policy = document.get("screen_policy") if document.get("screen_policy") in ("off", "bot-desktop") else "off"
timeout = document.get("readiness_timeout_s")
if not isinstance(timeout, int) or not 1 <= timeout <= 300:
    timeout = 30
print(record, policy, timeout)
PY
}

parse_runtime_options() {
  record=false
  record_set=false
  screen_policy=off
  screen_policy_set=false
  readiness_timeout_s=30
  readiness_timeout_set=false
  while [[ $# -gt 0 ]]; do
    case $1 in
      --record)
        record=true
        record_set=true
        ;;
      --screen-policy)
        shift
        [[ $# -gt 0 ]] || { printf '%s\n' '--screen-policy requires off or bot-desktop.' >&2; exit 2; }
        case $1 in
          off|bot-desktop) screen_policy=$1; screen_policy_set=true ;;
          *) printf '%s\n' '--screen-policy requires off or bot-desktop.' >&2; exit 2 ;;
        esac
        if [[ $screen_policy == bot-desktop ]]; then
          printf '%s\n' 'live desktop screen publication is not qualified under observer-only privacy contract.' >&2
          exit 2
        fi
        ;;
      --readiness-timeout-s)
        shift
        [[ $# -gt 0 && $1 =~ ^[0-9]+$ && $1 -ge 1 && $1 -le 300 ]] || {
          printf '%s\n' '--readiness-timeout-s requires an integer from 1 to 300.' >&2
          exit 2
        }
        readiness_timeout_s=$1
        readiness_timeout_set=true
        ;;
      *) printf '%s\n' 'Unexpected arguments.' >&2; exit 2 ;;
    esac
    shift
  done
}

service_active() {
  systemctl --user is-active "$unit"
}

case ${1:-} in
  --help|-h)
    reject_args "${@:2}"
    usage
    ;;
  start)
    shift
    parse_runtime_options "$@"
    write_settings "$record" "$screen_policy" "$readiness_timeout_s"
    systemctl --user import-environment DISPLAY XAUTHORITY
    systemctl --user start "$unit"
    service_active
    ;;
  stop)
    shift
    reject_args "$@"
    systemctl --user stop "$unit"
    ;;
  restart)
    shift
    parse_runtime_options "$@"
    if [[ $record_set == true || $screen_policy_set == true || $readiness_timeout_set == true ]]; then
      if [[ $record_set == false || $screen_policy_set == false || $readiness_timeout_set == false ]]; then
        read -r existing_record existing_policy existing_timeout <<<"$(read_existing_settings)"
        [[ $record_set == true ]] || record=$existing_record
        [[ $screen_policy_set == true ]] || screen_policy=$existing_policy
        [[ $readiness_timeout_set == true ]] || readiness_timeout_s=$existing_timeout
      fi
      write_settings "$record" "$screen_policy" "$readiness_timeout_s"
    fi
    systemctl --user restart "$unit"
    service_active
    ;;
  status)
    shift
    reject_args "$@"
    active=true
    active_state=$(systemctl --user is-active "$unit" 2>/dev/null) || active=false
    python3 - "$media/health.json" "$active" "$active_state" <<'PY'
import json
import sys
import time
from pathlib import Path

path = Path(sys.argv[1])
active = sys.argv[2] == "true"
active_state = sys.argv[3]
if path.is_file():
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        document = {"schema_version": 1, "state": "failed", "ready": False}
else:
    document = {"schema_version": 1, "state": "stopped", "ready": False}
document["service_active"] = active
document["service_state"] = active_state
print(json.dumps(document, sort_keys=True))
ready = document.get("state") == "ready" and document.get("ready") is True
published = document.get("published_at_unix_ms")
freshness = document.get("freshness", {})
workers = document.get("workers", {})
ready = ready and isinstance(published, int) and 0 <= time.time() * 1000 - published <= 5000
ready = ready and all(freshness.get(name, {}).get("fresh") is True for name in ("tracking", "activity"))
ready = ready and all(worker.get("status") == "running" for worker in workers.values())
raise SystemExit(0 if active and ready else 3)
PY
    ;;
  logs)
    shift
    reject_args "$@"
    journalctl --user -u "$unit" --no-pager -n 200
    ;;
  *)
    printf '%s\n' 'Unknown command; see --help.' >&2
    exit 2
    ;;
esac
