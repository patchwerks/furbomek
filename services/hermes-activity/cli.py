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
    character_session: Annotated[str | None, typer.Option("--character-session")] = None,
    hermes_session: Annotated[str | None, typer.Option("--hermes-session")] = None,
) -> None:
    """Consume Hermes events and publish one bounded activity projection."""
    if screen_policy is ScreenPolicy.BOT_DESKTOP:
        raise typer.BadParameter("bot-desktop capture is blocked until the authority/privacy contract is qualified")
    if character_session is not None and re.fullmatch(IDENTIFIER, character_session) is None:
        raise typer.BadParameter("character-session requires a bounded opaque identifier")
    if hermes_session is not None and re.fullmatch(IDENTIFIER, hermes_session) is None:
        raise typer.BadParameter("hermes-session requires a bounded opaque identifier")
    if hermes_session is not None and character_session is not None:
        raise typer.BadParameter("Hermes and character session modes are mutually exclusive")
    run(RunConfig(spool, profile_home, out_dir, once, screen_policy, character_session, hermes_session))


if __name__ == "__main__":
    app()
