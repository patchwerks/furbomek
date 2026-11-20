"""Deterministic schema exporter and offline pack boundary CLI."""

import json
from pathlib import Path
from typing import Annotated, Final

import typer
from pydantic import TypeAdapter

from .effect_contracts import AppliedAck, CapabilityDefinition, Effect
from .reaction_contracts import PrivateEvent, ReactionPack, parse_pack

DEFAULT_OUTPUT: Final = (
    Path(__file__).resolve().parents[4] / "packages/production-contracts"
)


def main(
    check: Annotated[bool, typer.Option("--check")] = False,
    output: Annotated[Path, typer.Option("--output")] = DEFAULT_OUTPUT,
    validate: Annotated[Path | None, typer.Option("--validate")] = None,
) -> None:
    """Export or compare bytes, or parse a local pack without contacting providers."""
    if validate is not None:
        with validate.open("rb") as source:
            pack = parse_pack(source.read(65537))
        typer.echo(
            json.dumps(
                {
                    "pack_id": pack.pack_id,
                    "horizon_ms": pack.horizon_ms,
                    "dispatch": False,
                },
                sort_keys=True,
            )
        )
        return
    schemas = {
        "effects.schema.json": TypeAdapter(Effect).json_schema(),
        "capability.schema.json": CapabilityDefinition.model_json_schema(),
        "applied-ack.schema.json": AppliedAck.model_json_schema(),
        "event.schema.json": PrivateEvent.model_json_schema(),
        "reaction.schema.json": ReactionPack.model_json_schema(),
    }
    for name, schema in sorted(schemas.items()):
        data = (
            json.dumps(schema, sort_keys=True, indent=2, ensure_ascii=True) + "\n"
        ).encode()
        target = output / name
        if check:
            if not target.is_file() or target.read_bytes() != data:
                typer.echo(f"schema drift: {name}", err=True)
                raise typer.Exit(1)
        else:
            output.mkdir(parents=True, exist_ok=True)
            _ = target.write_bytes(data)
    typer.echo("schemas verified" if check else "schemas exported")


if __name__ == "__main__":
    typer.run(main)
