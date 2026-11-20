"""Real isolated Godot process and bounded receipt polling."""

import os
import shutil
import subprocess
from collections.abc import Callable, Iterator
from pathlib import Path
from time import monotonic, sleep

import pytest

from furbomek_gateway.effect_contracts import GraphicsEffect
from furbomek_gateway.production_mailbox import PrivateMailbox
from furbomek_gateway.production_media import ProductionMedia
from furbomek_gateway.production_media_channel import MediaBinding
from furbomek_gateway.reaction_contracts import Cue
from furbomek_gateway.reaction_types import Dispatch, HostClock


def eventually[T](observe: Callable[[], T], accept: Callable[[T], bool]) -> T:
    until = monotonic() + 3
    while monotonic() < until:
        result = observe()
        if accept(result):
            return result
        sleep(0.01)
    pytest.fail("consumer did not reach the required observed state within 3 seconds")


@pytest.fixture
def media(tmp_path: Path) -> Iterator[ProductionMedia]:
    binary = os.environ.get("GODOT_BIN") or shutil.which("godot")
    if binary is None:
        pytest.fail("GODOT_BIN or godot is required for real media boundary tests")
    root = Path(__file__).resolve().parents[3]
    tmp_path.chmod(0o700)
    argv = [
        binary,
        "--headless",
        "--path",
        str(root / "tools/kinect2/godot"),
        "--script",
        "res://production_media_fixture.gd",
        "--",
        str(tmp_path),
    ]
    with (
        (tmp_path / "godot.log").open("w") as log,
        subprocess.Popen(  # noqa: S603 - explicit local Godot test binary, no shell.
            argv,
            stdout=log,
            stderr=subprocess.STDOUT,
        ) as process,
        PrivateMailbox(tmp_path) as mailbox,
    ):
        adapter = ProductionMedia(mailbox, HostClock(), MediaBinding("fixture-actor"))
        try:
            _ = eventually(lambda: adapter.available("graphics"), bool)
            yield adapter
        finally:
            _ = (tmp_path / "fixture-exit").write_text("stop")
            try:
                _ = process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                _ = process.wait(timeout=5)
            assert process.returncode == 0, (tmp_path / "godot.log").read_text()


def dispatch(media: ProductionMedia) -> Dispatch:
    effect = GraphicsEffect(
        capability="graphics.pulse.v1",
        preset="liquidation",
        intensity_percent=35,
        duration_ms=10000,
    )
    cue = Cue(
        id="fixture-cue",
        after=(),
        condition="always",
        ttl_ms=10000,
        on_unavailable="skip",
        on_fault="cancel_pack",
        effect=effect,
    )
    return Dispatch(
        owner="fixture-owner",
        cue=cue,
        resource="graphics",
        previous=media.snapshot("graphics"),
        deadline_ms=media.clock.monotonic_ms() + 2000,
    )
