"""Operator CLI for explicit app-window sharing and shutter control."""

from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path
from typing import Annotated, assert_never

import typer

from screen import CaptureError, invalidate_frames
from window_capture import list_windows, select_window
from window_consent import ConsentDocument, ConsentError, ConsentMode, WindowConsentStore

app = typer.Typer(add_completion=False)


class WindowAction(StrEnum):
    """Supported operator actions."""

    LIST = "list"
    SHARE = "share"
    SHUTTER = "shutter"
    RESUME = "resume"
    STATUS = "status"


@app.command()
def cli(
    profile_home: Path,
    out_dir: Path,
    action: WindowAction,
    window_id: Annotated[str | None, typer.Option("--window-id")] = None,
) -> None:
    """List, share, shutter, resume, or inspect one selected app window."""
    try:
        match action:
            case WindowAction.LIST:
                _list(profile_home)
                return
            case WindowAction.SHARE:
                selected_id = _parse_window_id(_require_window_id(window_id))
                document = WindowConsentStore(profile_home, out_dir).share(select_window(profile_home, selected_id))
            case WindowAction.SHUTTER:
                store = WindowConsentStore(profile_home, out_dir)
                document = store.shutter()
                invalidate_frames(out_dir)
            case WindowAction.RESUME:
                store = WindowConsentStore(profile_home, out_dir)
                selected_id = _parse_window_id(_require_window_id(window_id))
                document = store.resume(select_window(profile_home, selected_id))
            case WindowAction.STATUS:
                _status(WindowConsentStore(profile_home, out_dir).status(), profile_home)
                return
            case unreachable:
                assert_never(unreachable)
    except (CaptureError, ConsentError, OSError, ValueError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=2) from exc
    typer.echo(document.model_dump_json())


def _list(profile_home: Path) -> None:
    for entry in list_windows(profile_home):
        identity = entry.identity
        typer.echo(
            json.dumps(
                {
                    "window_id": identity.window_id,
                    "pid": identity.pid,
                    "width": identity.width,
                    "height": identity.height,
                    "instance": identity.instance,
                    "class": identity.class_name,
                },
                separators=(",", ":"),
            )
        )


def _status(document: ConsentDocument | None, profile_home: Path) -> None:
    if document is None:
        typer.echo('{"mode":"shuttered","selected":false}')
        return
    payload = document.model_dump()
    payload["selected_valid"] = False
    if document.mode is ConsentMode.SHARED and document.window_id is not None:
        try:
            selected = select_window(profile_home, document.window_id)
        except CaptureError:
            selected = None
        payload["selected_valid"] = (
            selected is not None
            and selected.pid == document.pid
            and selected.process_start_time == document.process_start_time
        )
    typer.echo(json.dumps(payload, separators=(",", ":")))


def _parse_window_id(raw: str) -> int:
    value = int(raw, 0)
    if value < 1:
        raise ConsentError("window-id must be positive")
    return value


def _require_window_id(window_id: str | None) -> str:
    if window_id is None:
        raise ConsentError("--window-id is required for share")
    return window_id


if __name__ == "__main__":
    app()
