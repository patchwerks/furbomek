"""Typer entry point for the locked Hermes activity broker."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from broker import RunConfig, run
from screen import ScreenPolicy

app = typer.Typer(add_completion=False)


@app.command()
def cli(
    spool: Path,
    profile_home: Path,
    out_dir: Path,
    once: Annotated[bool, typer.Option("--once")] = False,
    screen_policy: Annotated[ScreenPolicy, typer.Option("--screen-policy")] = ScreenPolicy.OFF,
) -> None:
    """Consume Hermes events and publish one bounded activity projection."""
    if screen_policy is ScreenPolicy.BOT_DESKTOP:
        raise typer.BadParameter("bot-desktop capture is blocked until the authority/privacy contract is qualified")
    run(RunConfig(spool, profile_home, out_dir, once, screen_policy))


if __name__ == "__main__":
    app()
