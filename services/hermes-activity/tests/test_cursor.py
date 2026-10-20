from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cursor import CursorSnapshot, IncrementalSpoolReader
from hermes_feed import SpoolEvent


def line(call: str, *, detail: str = "") -> bytes:
    return (
        SpoolEvent(
            kind="tool",
            ts_ms=1_700_000_000_000,
            session="s",
            phase="running",
            category="BROWSER",
            action="opening",
            detail=detail,
            call=call,
        )
        .model_dump_json()
        .encode()
        + b"\n"
    )


def test_cursor_waits_for_partial_and_drains_rotation(tmp_path: Path) -> None:
    spool = tmp_path / "events.jsonl"
    spool.write_bytes(line("a") + line("b")[:-1])
    reader = IncrementalSpoolReader(spool, CursorSnapshot(None, 0))

    first = reader.poll()
    assert [event.call for event in first.events] == ["a"]
    for _ in range(3):
        partial = reader.poll()
        assert partial.events == ()
        assert not partial.uncertain
    with spool.open("ab") as stream:
        stream.write(b"\n")
    complete = reader.poll()
    assert [event.call for event in complete.events] == ["b"]

    rotated = tmp_path / "events.old"
    spool.write_bytes(spool.read_bytes() + line("c"))
    spool.replace(rotated)
    spool.write_bytes(line("d"))
    drained = reader.poll()
    assert [event.call for event in drained.events] == ["c", "d"]
    reader.close()


def test_rotation_with_unfinished_record_is_uncertain(tmp_path: Path) -> None:
    spool = tmp_path / "events.jsonl"
    spool.write_bytes(line("partial")[:-1])
    reader = IncrementalSpoolReader(spool, CursorSnapshot(None, 0))
    assert reader.poll().events == ()
    spool.replace(tmp_path / "events.old")
    spool.write_bytes(line("new"))
    rotated = reader.poll()
    assert [event.call for event in rotated.events] == ["new"]
    assert rotated.uncertain
    reader.close()


def test_cursor_restart_does_not_replay_and_truncation_latches_uncertainty(tmp_path: Path) -> None:
    spool = tmp_path / "events.jsonl"
    spool.write_bytes(line("a"))
    reader = IncrementalSpoolReader(spool, CursorSnapshot(None, 0))
    first = reader.poll()
    restarted = IncrementalSpoolReader(spool, first.cursor)
    assert restarted.poll().events == ()

    with spool.open("ab") as stream:
        stream.write(line("b"))
    after_restart = restarted.poll()
    assert [event.call for event in after_restart.events] == ["b"]

    spool.write_bytes(line("c"))
    truncated = restarted.poll()
    assert [event.call for event in truncated.events] == ["c"]
    assert truncated.uncertain
    reader.close()
    restarted.close()


def test_cursor_skips_malformed_and_oversized_complete_records_once(tmp_path: Path) -> None:
    spool = tmp_path / "events.jsonl"
    spool.write_bytes(b"not-json\n" + b"x" * 4_097 + b"\n" + line("safe"))
    reader = IncrementalSpoolReader(spool, CursorSnapshot(None, 0))
    result = reader.poll()
    assert [event.call for event in result.events] == ["safe"]
    assert result.uncertain
    reader.close()


def test_oversized_partial_record_advances_without_repeating(tmp_path: Path) -> None:
    spool = tmp_path / "events.jsonl"
    spool.write_bytes(b"x" * 5_000)
    reader = IncrementalSpoolReader(spool, CursorSnapshot(None, 0))
    first = reader.poll()
    assert first.events == ()
    assert first.uncertain
    for _ in range(2):
        clean = reader.poll()
        assert clean.events == ()
        assert not clean.uncertain
    with spool.open("ab") as stream:
        stream.write(b"\n" + line("safe"))
    recovered = reader.poll()
    assert [event.call for event in recovered.events] == ["safe"]
    assert recovered.cursor.offset == spool.stat().st_size
    reader.close()
    restarted = IncrementalSpoolReader(spool, recovered.cursor)
    assert restarted.poll().events == ()
    restarted.close()


def test_oversize_cursor_restart_before_newline_does_not_replay(tmp_path: Path) -> None:
    spool = tmp_path / "events.jsonl"
    spool.write_bytes(b"x" * 5_000)
    reader = IncrementalSpoolReader(spool, CursorSnapshot(None, 0))
    checkpoint = reader.poll().cursor
    reader.close()
    restarted = IncrementalSpoolReader(spool, checkpoint)
    assert restarted.poll().events == ()
    with spool.open("ab") as stream:
        stream.write(b"x" * 1_000)
    assert restarted.poll().events == ()
    with spool.open("ab") as stream:
        stream.write(b"\n" + line("safe"))
    consumed = restarted.poll()
    assert [event.call for event in consumed.events] == ["safe"]
    assert consumed.cursor.offset == spool.stat().st_size
    restarted.close()
    final_reader = IncrementalSpoolReader(spool, consumed.cursor)
    assert final_reader.poll().events == ()
    final_reader.close()
