"""Local signed-fixture probe; performs no provider traffic or reaction dispatch."""

from pathlib import Path
from typing import Annotated, Literal, assert_never

import typer
from pydantic import ValidationError

from .auth import MAX_BYTES, parse
from .contracts import SourceRejectedError
from .hyperliquid import HyperliquidAdapter, HyperliquidPolicy
from .twitch import TwitchAdapter, TwitchPolicy


def probe(
    provider: Annotated[Literal["twitch", "hyperliquid"], typer.Argument()],
    policy_file: Annotated[Path, typer.Option()],
    delivery_file: Annotated[Path, typer.Option()],
    key_file: Annotated[Path, typer.Option()],
    now_ms: Annotated[int, typer.Option()],
) -> None:
    """Print only redacted results for a bounded local authenticated delivery."""
    try:
        with delivery_file.open("rb") as stream:
            raw = stream.read(MAX_BYTES + 1)
        with key_file.open("rb") as stream:
            key = stream.read(33)
        with policy_file.open("rb") as stream:
            policy_raw = stream.read(MAX_BYTES + 1)
        match provider:
            case "twitch":
                twitch = TwitchAdapter(parse(TwitchPolicy, policy_raw), key)
                results = (twitch.receive(raw, now_ms),)
            case "hyperliquid":
                hyperliquid = HyperliquidAdapter(
                    parse(HyperliquidPolicy, policy_raw), key
                )
                results = hyperliquid.receive(raw, now_ms)
            case _:
                assert_never(provider)
        for result in results:
            typer.echo(result.model_dump_json())
        if any(result.status == "denied" for result in results):
            raise typer.Exit(2)
    except (OSError, ValueError, ValidationError, SourceRejectedError):
        typer.echo('{"status":"denied","reason":"configuration"}')
        raise typer.Exit(2) from None


if __name__ == "__main__":
    typer.run(probe)
