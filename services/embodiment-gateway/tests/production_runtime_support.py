"""Isolated real Godot consumer and private production runtime for transport QA."""

import os
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest
from pydantic import SecretStr

from furbomek_gateway.edge_host import EdgeHost, EdgeSettings
from furbomek_gateway.edge_media import MediaSettings
from furbomek_gateway.edge_ssh import LinkSettings
from furbomek_gateway.production_lifecycle import ProductionLifetime, ProductionSettings
from furbomek_gateway.reaction_contracts import parse_pack
from tests.guard_settings import powered_settings
from tests.production_media_support import eventually


@pytest.fixture
def production(tmp_path: Path) -> Iterator[ProductionLifetime]:
    binary = os.environ.get("GODOT_BIN") or shutil.which("godot")
    if binary is None:
        pytest.fail("real Godot fixture requires GODOT_BIN")
    root = Path(__file__).resolve().parents[3]
    mailbox = tmp_path / "mailbox"
    mailbox.mkdir(mode=0o700)
    settings = ProductionSettings(
        mailbox=mailbox,
        state=tmp_path / "private",
        actor_id="transport-fixture",
        http_bootstrap=SecretStr("fixture-owner-bootstrap-secret-at-least32"),
        packs=tuple(
            parse_pack(
                (root / "packages/production-contracts/presets" / name).read_bytes()
            )
            for name in ("liquidation.json", "viewer-reaction.json")
        ),
    )
    argv = [
        binary,
        "--headless",
        "--path",
        str(root / "tools/kinect2/godot"),
        "--script",
        "res://production_media_fixture.gd",
        "--",
        str(mailbox),
    ]
    with (
        (tmp_path / "godot.log").open("w") as log,
        subprocess.Popen(  # noqa: S603 - isolated local consumer, no shell.
            argv, stdout=log, stderr=subprocess.STDOUT
        ) as consumer,
    ):
        _ = (tmp_path / "consumer.pid").write_text(str(consumer.pid))
        try:
            with ProductionLifetime(settings) as lifetime:
                _ = eventually(
                    lambda: lifetime.runtime.status().health,
                    lambda state: state == "fresh",
                )
                yield lifetime
        finally:
            _ = (mailbox / "fixture-exit").write_text("stop")
            try:
                _ = consumer.wait(timeout=5)
            except subprocess.TimeoutExpired:
                consumer.kill()
                _ = consumer.wait(timeout=5)
            assert consumer.returncode == 0, (tmp_path / "godot.log").read_text()


def edge(production: ProductionLifetime, directory: Path) -> EdgeHost:
    missing = directory / "unconfigured-device"
    return EdgeHost(
        EdgeSettings(
            media=MediaSettings(
                runtime=directory,
                repository=missing,
                media_root=missing,
                capture=missing,
                tracker_python=missing,
                godot=missing,
            ),
            guard=powered_settings(str(missing)),
            link=LinkSettings(host="unconfigured", relay_command=("false",)),
        ),
        production,
    )
