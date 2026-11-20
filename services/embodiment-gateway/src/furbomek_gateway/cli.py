"""Typer entrypoint for the stdio MCP server."""

import sys
from pathlib import Path
from typing import Annotated

import anyio
import typer
from pydantic import ValidationError

from furbomek_gateway.config_overlay import (
    ConfigOverlayError,
    McpServerEntry,
    overlay_mcp_server,
)
from furbomek_gateway.edge_client import create_edge_client
from furbomek_gateway.edge_host import EdgeSettings, run_edge
from furbomek_gateway.edge_protocol import OperatorRequest, exchange, unix_ms
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


@app.command("edge-mcp")
def edge_mcp(socket: Path, production: bool = False) -> None:
    """Serve the narrow Mac edge tools from the Brodex profile."""
    create_edge_client(socket, production=production).run(transport="stdio")


@app.command("edge-host")
def edge_host(settings: Path) -> None:
    """Run the Mac edge and its existing-account reverse SSH tunnel."""
    try:
        config = EdgeSettings.model_validate_json(settings.read_bytes())
        anyio.run(run_edge, config)
    except (OSError, ValidationError):
        raise typer.Exit(code=2) from None


@app.command("edge-operator")
def edge_operator(socket: Path, command: str) -> None:
    """Open, enable, or close a bench window from the local operator session."""
    try:
        request = OperatorRequest.model_validate(
            {"command": command, "issued_ms": unix_ms()}
        )
    except ValidationError:
        raise typer.Exit(code=2) from None
    reply = anyio.run(exchange, socket, request)
    typer.echo(reply.model_dump_json(exclude_none=True))
    if reply.result != "ok":
        raise typer.Exit(code=1)


def main() -> None:
    """Run the furbomek-gateway command."""
    app()
