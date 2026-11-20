# /// script
# requires-python = ">=3.12"
# dependencies = ["pydantic==2.14.3"]
# ///
# Run: python3 tools/kinect2/effects/validate_inventory.py
# Or: uv run tools/kinect2/effects/validate_inventory.py --fixture mislabeled-depth
"""Validate capability provenance, not runtime health or physical accuracy."""

import json
import sys
from datetime import date
from pathlib import Path
from typing import Annotated, ClassVar, Final, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator
from pydantic_core import PydanticCustomError

Text = Annotated[str, Field(min_length=1)]
Origin = Literal["sensor", "capture", "derived", "renderer", "program", "sdk"]
Representation = Literal[
    "rgb",
    "infrared",
    "depth",
    "registered_rgb",
    "measured_xyz",
    "rgb_derived",
    "inference",
    "presentation",
    "audio",
    "control",
]
ROOT: Final = Path(__file__).resolve().parent
DEPTH_SIZE: Final = (512, 424)
RGB_SIZE: Final = (1920, 1080)
OPTION_ARGUMENTS: Final = 2


class Model(BaseModel):
    """Immutable catalog boundary; reject undocumented fields and coercion."""

    model_config: ClassVar[ConfigDict] = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
    )


class Feed(Model):
    """Physical or software input with its own sample grid."""

    kind: Literal[
        "rgb",
        "ir",
        "depth",
        "registered_rgb",
        "registered_depth",
        "tracking",
        "activity",
        "rendered_program",
        "microphone",
        "sdk",
        "none",
    ]
    resolution: tuple[int, int] | None

    @model_validator(mode="after")
    def check_native_grid(self) -> Self:
        """Prevent native optical and depth grids being interchanged."""
        if (
            self.kind in {"depth", "ir", "registered_rgb", "registered_depth"}
            and self.resolution != DEPTH_SIZE
        ):
            code = "native_depth_grid_required"
            raise PydanticCustomError(code, code)
        if self.kind == "rgb" and self.resolution != RGB_SIZE:
            code = "native_rgb_grid_required"
            raise PydanticCustomError(code, code)
        if self.resolution is not None and min(self.resolution) <= 0:
            code = "positive_resolution_required"
            raise PydanticCustomError(code, code)
        return self


class Availability(Model):
    """Platform-specific implementation state, never live admission."""

    state: Literal[
        "implemented", "reference_only", "unsupported", "unverified", "proposed"
    ]
    reason: Text


class Capability(Model):
    """One capability retaining data origin and evidence limitations."""

    id: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_-]+$")]
    label: Text
    origin: Origin
    input: Feed
    representation: Representation
    max_measured_depth_samples: int = Field(ge=0, le=217088)
    mac: Availability
    linux: Availability
    control: Text
    limits: Text
    evidence: tuple[Text, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def check_measurement_provenance(self) -> Self:
        """Optical styling and inferred tracks cannot acquire measured XYZ."""
        depth_claim = self.representation in {"depth", "measured_xyz"}
        if depth_claim or self.max_measured_depth_samples > 0:
            if self.input.kind not in {"depth", "registered_depth"}:
                code = "measured_depth_requires_depth_input"
                raise PydanticCustomError(code, code)
            if self.origin not in {"sensor", "capture", "renderer"}:
                code = "inference_is_not_sensor_measurement"
                raise PydanticCustomError(code, code)
        if depth_claim and self.max_measured_depth_samples == 0:
            code = "depth_claim_requires_native_sample_bound"
            raise PydanticCustomError(code, code)
        return self


class Inventory(Model):
    """Catalog seed independently versioned from future runtime contracts."""

    schema_version: Literal["furbomek.kinect-inventory.v1"]
    reviewed_at: date
    source_revision: Annotated[str, Field(pattern=r"^[0-9a-f]{40}$")]
    scope: Literal["implementation_inventory_not_live_admission"]
    entries: tuple[Capability, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_ids(self) -> Self:
        """Require unambiguous capability selection."""
        ids = [entry.id for entry in self.entries]
        if len(ids) != len(set(ids)):
            code = "duplicate_capability_id"
            raise PydanticCustomError(code, code)
        return self


def main() -> int:
    """Read one inventory or the deliberately invalid provenance fixture."""
    arguments = sys.argv[1:]
    path = ROOT / "inventory.json"
    if arguments == ["--fixture", "mislabeled-depth"]:
        path = ROOT / "fixtures/mislabeled-depth.json"
    elif len(arguments) == OPTION_ARGUMENTS and arguments[0] == "--inventory":
        path = Path(arguments[1])
    elif arguments:
        _ = sys.stdout.write(
            json.dumps(
                {
                    "valid": False,
                    "error": "usage",
                    "usage": (
                        "validate_inventory.py [--inventory PATH | "
                        "--fixture mislabeled-depth]"
                    ),
                }
            )
            + "\n"
        )
        return 2
    try:
        catalog = Inventory.model_validate_json(path.read_bytes())
    except ValidationError as error:
        _ = sys.stdout.write(
            json.dumps(
                {
                    "valid": False,
                    "errors": error.errors(include_input=False, include_url=False),
                }
            )
            + "\n"
        )
        return 2
    except OSError as error:
        _ = sys.stdout.write(
            json.dumps({"valid": False, "error": error.strerror}) + "\n"
        )
        return 2
    _ = sys.stdout.write(
        json.dumps(
            {"valid": True, "entries": len(catalog.entries), "scope": catalog.scope}
        )
        + "\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
