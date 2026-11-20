"""Explicit injected HTTP/browser fixture. No devices or default runtime backend."""

import os
import sys
from pathlib import Path
from threading import Thread

from pydantic import SecretStr

from furbomek_gateway.production_http import OwnerHttpServer

from .production_http_fixture_controller import FixtureController


def main() -> None:
    """Private test bootstrap via environment, never emitted in logs/evidence."""
    root = Path(__file__).resolve().parents[3] / "apps/production-studio/dist"
    controller = FixtureController()
    server = OwnerHttpServer(
        controller,
        SecretStr(os.environ["TASK24_FIXTURE_BOOTSTRAP"]),
        studio_directory=root,
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    _ = sys.stdout.write(server.origin + "\n")
    _ = sys.stdout.flush()
    try:
        for line in sys.stdin:
            command = line.strip()
            with server.operation:
                if command == "held":
                    controller.state = controller.state.model_copy(
                        update={"health": "held"}
                    )
                elif command == "override":
                    controller.state = controller.state.model_copy(
                        update={"revision": controller.state.revision + 1}
                    )
                elif command == "fresh":
                    controller.state = controller.state.model_copy(
                        update={"health": "fresh"}
                    )
                elif command == "stop":
                    break
            _ = sys.stdout.write("updated\n")
            _ = sys.stdout.flush()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


if __name__ == "__main__":
    main()
