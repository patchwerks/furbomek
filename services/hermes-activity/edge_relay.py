"""Brodex endpoint for the Mac's reverse SSH socket and public HUD feed."""

import fcntl
import os
import select
import stat
import sys
from pathlib import Path
from tempfile import mkdtemp
from typing import Final

from activity_models import ActivityEvent
from runtime import ActivityBroker, RunConfig, SystemClock

_MESSAGE_LIMIT: Final = 8192
_CREATE_ARG_COUNT: Final = 5
_ATTACH_ARG_COUNT: Final = 6


def _private(path: Path) -> None:
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        message = "Brodex edge directory is not owner-only"
        raise SystemExit(message)


def _relay(root: Path, session: Path, config: RunConfig) -> None:
    _private(session)
    if session.parent != root or not session.name.startswith("link."):
        message = "Invalid reverse socket directory"
        raise SystemExit(message)
    listener = session / "control.sock"
    info = listener.lstat()
    if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        message = "Reverse socket is not owner-only"
        raise SystemExit(message)
    link = root / "current"
    pending = session / "current.next"
    with (root / "relay.lock").open("ab") as ownership:
        fcntl.flock(ownership.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        broker = ActivityBroker(config)
        try:
            pending.symlink_to(session)
            pending.replace(link)
            sys.stdout.write("READY\n")
            sys.stdout.flush()
            last: bytes | None = None
            clock = SystemClock()
            while not select.select([sys.stdin], [], [], 0.12)[0]:
                broker.step(clock.now_ms())
                with (config.out_dir / "activity.json").open("rb") as publication:
                    raw = publication.read(_MESSAGE_LIMIT + 1)
                if raw == last or len(raw) > _MESSAGE_LIMIT:
                    continue
                event = ActivityEvent.model_validate_json(raw)
                text_only = event.model_dump_json(exclude={"payload": {"screen"}}, by_alias=True)
                sys.stdout.write(text_only + "\n")
                sys.stdout.flush()
                last = raw
        finally:
            broker.reader.close()
            if link.is_symlink() and link.readlink() == session:
                link.unlink()
            listener.unlink(missing_ok=True)
            pending.unlink(missing_ok=True)
            session.rmdir()


def main() -> None:
    """Run a fixed create or attach command within one SSH session."""
    os.umask(0o077)
    if len(sys.argv) not in (_CREATE_ARG_COUNT, _ATTACH_ARG_COUNT):
        message = "Usage: edge_relay.py STATE PROFILE SPOOL create|attach [SESSION]"
        raise SystemExit(message)
    root, profile, spool = (Path(value) for value in sys.argv[1:4])
    _private(root)
    command = sys.argv[4]
    if command == "create" and len(sys.argv) == _CREATE_ARG_COUNT:
        _ = sys.stdout.write(mkdtemp(prefix="link.", dir=root) + "\n")
    elif command == "attach" and len(sys.argv) == _ATTACH_ARG_COUNT:
        _relay(root, Path(sys.argv[5]), RunConfig(spool, profile, root / "hud"))
    else:
        message = "Unknown Brodex edge operation"
        raise SystemExit(message)


if __name__ == "__main__":
    main()
