"""Typer entry point for the locked Hermes activity broker."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Annotated

import typer

from broker import RunConfig, run
from character_state import IDENTIFIER
from screen import ScreenPolicy

app = typer.Typer(add_completion=False)


@app.command()
def cli(  # noqa: PLR0913 - Keep the existing CLI positional interface plus explicit opt-in flags.
    spool: Path,
    profile_home: Path,
    out_dir: Path,
    once: Annotated[bool, typer.Option("--once")] = False,
    screen_policy: Annotated[ScreenPolicy, typer.Option("--screen-policy")] = ScreenPolicy.OFF,
    window_id: Annotated[str | None, typer.Option("--window-id")] = None,
    character_session: Annotated[str | None, typer.Option("--character-session")] = None,
) -> None:
    """Consume Hermes events and publish one bounded activity projection."""
    if screen_policy is ScreenPolicy.BOT_DESKTOP:
        raise typer.BadParameter("bot-desktop capture is blocked until the authority/privacy contract is qualified")
    try:
        selected_window_id = None if window_id is None else int(window_id, 0)
    except ValueError as error:
        raise typer.BadParameter("window-id must be a positive X11 identifier") from error
    if selected_window_id is not None and selected_window_id < 1:
        raise typer.BadParameter("window-id must be a positive X11 identifier")
    if character_session is not None and re.fullmatch(IDENTIFIER, character_session) is None:
        raise typer.BadParameter("character-session requires a bounded opaque identifier")
    run(RunConfig(spool, profile_home, out_dir, once, screen_policy, character_session, selected_window_id))


if __name__ == "__main__":
    app()
