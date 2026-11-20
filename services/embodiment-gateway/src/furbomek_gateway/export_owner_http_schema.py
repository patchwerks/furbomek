"""Export/check the owner HTTP schemas consumed by the isolated studio."""

import argparse
import json
from pathlib import Path

from .framing_models import FramingPreset, Manual
from .production_http_models import ACTION, OwnerResult, OwnerState
from .production_media_contracts import VisualSettings


class Arguments(argparse.Namespace):
    """Typed argparse destination."""

    path: Path = Path()
    check: bool = False


def main() -> None:
    """Export to an explicit local build artifact; no runtime access."""
    parser = argparse.ArgumentParser()
    _ = parser.add_argument("path", type=Path)
    _ = parser.add_argument("--check", action="store_true")
    args = parser.parse_args(namespace=Arguments())
    schemas = {
        "ownerState": OwnerState.model_json_schema(),
        "ownerResult": OwnerResult.model_json_schema(),
        "ownerAction": ACTION.json_schema(),
        "framingPreset": FramingPreset.model_json_schema(),
        "manual": Manual.model_json_schema(),
        "visualSettings": VisualSettings.model_json_schema(),
    }
    content = json.dumps(schemas, indent=2, sort_keys=True) + "\n"
    path = Path(str(args.path))
    if args.check:
        if path.read_text() != content:
            msg = "owner HTTP schema drift"
            raise ValueError(msg)
    else:
        _ = path.write_text(content)


if __name__ == "__main__":
    main()
