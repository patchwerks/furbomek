"""Fixed local sanitized scheduler observation, pending explicit broker enrollment."""

import os
from pathlib import Path
from typing import Annotated, Literal
from uuid import uuid4

from pydantic import Field

from .effect_contracts import Contract
from .reaction_types import Projection


class ProductionProjection(Contract):
    """Closed observed statuses only; never event IDs, raw activity or authority."""

    schema_version: Literal["furbomek.production-projection.v1"] = (
        "furbomek.production-projection.v1"
    )
    published_ms: int = Field(ge=0)
    ttl_ms: Literal[1000] = 1000
    stage: Literal["HOLD"] = "HOLD"
    broker: Literal["HOLD_not_enrolled"] = "HOLD_not_enrolled"
    reactions: Annotated[tuple[Projection, ...], Field(max_length=64)]


def publish(directory: Path, projection: ProductionProjection) -> None:
    """Atomically write one fixed file beneath the validated private state root."""
    path = directory / f".projection-{uuid4().hex}"
    try:
        with os.fdopen(
            os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600),
            "w",
        ) as file:
            _ = file.write(projection.model_dump_json())
            file.flush()
            os.fsync(file.fileno())
        _ = path.replace(directory / "production-projection.json")
    finally:
        path.unlink(missing_ok=True)
