"""Typer entrypoint for the stdio MCP server."""

import sys
from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError

from furbomek_gateway.config_overlay import (
    ConfigOverlayError,
    McpServerEntry,
    overlay_mcp_server,
)
from furbomek_gateway.guard_server import create_guard_server
from furbomek_gateway.plugin_overlay import ObserverOverlayError, overlay_observer
from furbomek_gateway.server import create_server
from furbomek_gateway.settings import (
    SettingsLoadError,
    load_guard_settings,
    load_settings,
)

app = typer.Typer(add_completion=False, no_args_is_help=True)


@app.callback()
def _root() -> None:
    pass


@app.command()
def serve(
    settings: Annotated[
        Path,
        typer.Option("--settings", exists=True, dir_okay=False, readable=True),
    ],
) -> None:
    """Run the MCP server over stdio using operator-local JSON settings."""
    try:
        loaded_settings = load_settings(settings)
    except SettingsLoadError:
        raise typer.Exit(code=2) from None
    create_server(loaded_settings).run(transport="stdio")


@app.command("serve-guard")
def serve_guard(
    settings: Annotated[
        Path,
        typer.Option("--settings", exists=True, dir_okay=False, readable=True),
    ],
) -> None:
    """Run the isolated operator-configured Guard MCP server over stdio."""
    try:
        loaded_settings = load_guard_settings(settings)
    except SettingsLoadError:
        raise typer.Exit(code=2) from None
    create_guard_server(loaded_settings).run(transport="stdio")


@app.command()
def overlay(
    entry: Annotated[
        Path,
        typer.Option("--entry", exists=True, dir_okay=False, readable=True),
    ],
) -> None:
    """Transform Hermes YAML on stdin for Chezmoi without storing user secrets."""
    try:
        server_entry = McpServerEntry.model_validate_json(entry.read_text("utf-8"))
        result = overlay_mcp_server(sys.stdin.read(), server_entry)
    except (OSError, UnicodeError, ValidationError, ConfigOverlayError):
        raise typer.Exit(code=2) from None
    _ = sys.stdout.write(result)


@app.command("overlay-observer")
def overlay_observer_command() -> None:
    """Transform Hermes YAML to enroll the managed observer plugin."""
    try:
        result = overlay_observer(sys.stdin.read())
    except (ObserverOverlayError, UnicodeError):
        raise typer.Exit(code=2) from None
    _ = sys.stdout.write(result)


def main() -> None:
    """Run the furbomek-gateway command."""
    app()
