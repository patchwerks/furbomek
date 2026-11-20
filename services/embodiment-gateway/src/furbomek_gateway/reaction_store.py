"""Atomic private SQLite admissions, resource reservations and step journal."""

import fcntl
import os
import sqlite3
import stat
from collections.abc import Generator
from contextlib import ExitStack, closing, contextmanager
from pathlib import Path
from types import TracebackType
from typing import Final, Self, final

from .effect_contracts import capability_definition
from .reaction_contracts import PrivateEvent, ReactionPack
from .reaction_types import PropertyState, Reservation, Step, StorePrivacyError

DIRECTORY_MODE: Final = 0o700
FILE_MODE: Final = 0o600


@final
class ReactionStore:
    """Short transactions; journal is durable before any adapter side effect.

    The parent must be owner-only, outside Git. DELETE journals inherit 0600
    from the precreated DB; FULL sync covers each reservation/transition.
    """

    def __init__(self, path: Path) -> None:
        """Open only a private non-repository state path."""
        self.path = path.absolute()
        self._resources = ExitStack()
        if any((parent / ".git").exists() for parent in self.path.resolve().parents):
            raise StorePrivacyError(str(self.path))
        self.path.parent.mkdir(mode=DIRECTORY_MODE, parents=True, exist_ok=True)
        parent = self.path.parent.lstat()
        if (
            not stat.S_ISDIR(parent.st_mode)
            or parent.st_uid != os.getuid()
            or stat.S_IMODE(parent.st_mode) != DIRECTORY_MODE
        ):
            raise StorePrivacyError(str(self.path.parent))
        flags = os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW
        with os.fdopen(os.open(self.path, flags, FILE_MODE), "rb") as handle:
            info = os.fstat(handle.fileno())
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) != FILE_MODE
                or info.st_nlink != 1
            ):
                raise StorePrivacyError(str(self.path))
        with self.transaction() as db:
            _ = db.executescript("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL, scope TEXT NOT NULL, stable_id TEXT NOT NULL,
                    retain_until INTEGER NOT NULL,
                    UNIQUE(source, scope, stable_id));
                CREATE TABLE IF NOT EXISTS steps (
                    owner TEXT PRIMARY KEY, event_id INTEGER NOT NULL,
                    ordinal INTEGER NOT NULL, resource TEXT NOT NULL,
                    status TEXT NOT NULL, data TEXT NOT NULL,
                    FOREIGN KEY(event_id) REFERENCES events(id) ON DELETE CASCADE);
                CREATE UNIQUE INDEX IF NOT EXISTS active_resource ON steps(resource)
                    WHERE status IN ('reserved','dispatched','applied');
            """)

    def __enter__(self) -> Self:
        """Own runtime lease resources until exit."""
        return self

    def __exit__(
        self,
        _kind: type[BaseException] | None,
        _error: BaseException | None,
        _traceback: TracebackType | None,
    ) -> None:
        """Release the exclusive runtime lease; transactions close independently."""
        self._resources.close()

    def claim_scheduler(self) -> None:
        """Exclude a second scheduler, including another process, from recovery."""
        path = self.path.with_suffix(".scheduler-lock")
        handle = self._resources.enter_context(
            os.fdopen(
                os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, FILE_MODE), "rb"
            )
        )
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Connection]:
        """Serialize writers across processes; commit only complete transitions."""
        with closing(sqlite3.connect(self.path, timeout=5)) as db, db:
            _ = db.execute("PRAGMA foreign_keys=ON")
            _ = db.execute("PRAGMA synchronous=FULL")
            _ = db.execute("BEGIN IMMEDIATE")
            yield db

    def admit(
        self, event: PrivateEvent, pack: ReactionPack, timing: Reservation
    ) -> int | None:
        """Reserve trusted source identity and the entire finite graph atomically."""
        with self.transaction() as db:
            cursor = db.execute(
                """INSERT OR IGNORE INTO events(source,scope,stable_id,retain_until)
                VALUES(?,?,?,?)""",
                (*event.dedupe_key, event.retain_until_ms),
            )
            if cursor.rowcount != 1:
                return None
            event_id = cursor.lastrowid
            if event_id is None:
                msg = "missing admission identity"
                raise sqlite3.DatabaseError(msg)
            ends: dict[str, int] = {}
            pending = list(enumerate(pack.cues))
            while pending:
                ready = [
                    (i, cue) for i, cue in pending if set(cue.after) <= ends.keys()
                ]
                for ordinal, cue in ready:
                    offset = max((ends[key] for key in cue.after), default=0)
                    ends[cue.id] = offset + cue.effect.duration_ms
                    definition = capability_definition(cue.effect.capability)
                    step = Step(
                        owner=f"r{event_id}-s{ordinal}",
                        event_id=event_id,
                        ordinal=ordinal,
                        cue=cue,
                        resource=definition.resource,
                        priority=timing.priority,
                        due_ms=timing.now_ms + offset,
                        deadline_ms=timing.now_ms
                        + min(timing.age_budget_ms, offset + cue.ttl_ms),
                    )
                    _ = db.execute(
                        "INSERT INTO steps VALUES(?,?,?,?,?,?)",
                        (
                            step.owner,
                            event_id,
                            ordinal,
                            step.resource,
                            step.status,
                            step.model_dump_json(),
                        ),
                    )
                    pending.remove((ordinal, cue))
            return event_id

    def steps(self) -> tuple[Step, ...]:
        """Read private state in deterministic admission/cue order."""
        with self.transaction() as db:
            rows: list[tuple[str]] = db.execute(
                "SELECT data FROM steps ORDER BY event_id, ordinal"
            ).fetchall()
            return tuple(Step.model_validate_json(row[0]) for row in rows)

    def reserve(self, step: Step, previous: PropertyState | None) -> bool:
        """One-shot pending -> reserved transition with a cross-event resource lock."""
        if step.status != "pending":
            return False
        reserved = step.model_copy(update={"status": "reserved", "previous": previous})
        with self.transaction() as db:
            busy: list[tuple[int]] = db.execute(
                """SELECT 1 FROM steps WHERE resource=? AND status IN
                ('reserved','dispatched','applied')""",
                (step.resource,),
            ).fetchall()
            if busy:
                return False
            cursor = db.execute(
                "UPDATE steps SET status=?,data=? WHERE owner=? AND data=?",
                (
                    reserved.status,
                    reserved.model_dump_json(),
                    step.owner,
                    step.model_dump_json(),
                ),
            )
            return cursor.rowcount == 1

    def transition(self, before: Step, after: Step) -> bool:
        """CAS the full persisted record; stale ACKs cannot replace cancellation."""
        with self.transaction() as db:
            cursor = db.execute(
                "UPDATE steps SET status=?,data=? WHERE owner=? AND data=?",
                (
                    after.status,
                    after.model_dump_json(),
                    before.owner,
                    before.model_dump_json(),
                ),
            )
            return cursor.rowcount == 1

    def prune(self, epoch_ms: int) -> int:
        """Retain dedupe until the reconnect window AND all steps are terminal."""
        with self.transaction() as db:
            cursor = db.execute(
                """DELETE FROM events WHERE retain_until<? AND NOT EXISTS
                (SELECT 1 FROM steps WHERE steps.event_id=events.id AND status IN
                ('pending','reserved','dispatched','applied'))""",
                (epoch_ms,),
            )
            return cursor.rowcount
