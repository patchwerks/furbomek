"""Real HTTP asset boundary checks using explicit owner build directories."""

from pathlib import Path

import pytest

from furbomek_gateway.production_http_assets import MAX_FILE_BYTES

from .production_http_wire import exchange, login, running


def build(directory: Path) -> None:
    _ = (directory / "index.html").write_text('<script src="/assets/main.js"></script>')
    (directory / "assets").mkdir()
    _ = (directory / "assets/main.js").write_text("document.title = 'Owner';")
    _ = (directory / "private.txt").write_text("never served")


def test_assets_are_exact_immutable_same_origin_and_framing_denied(
    tmp_path: Path,
) -> None:
    build(tmp_path)
    with running(studio_directory=tmp_path) as (server, _, token):
        status, body, headers = exchange(server, "/?mode=live")
        assert status == 200
        assert b"/assets/main.js" in body
        assert "frame-ancestors 'none'" in headers["Content-Security-Policy"]
        assert "script-src 'self'" in headers["Content-Security-Policy"]
        _ = (tmp_path / "assets/main.js").write_text("changed after startup")
        status, body, _ = exchange(server, "/assets/main.js")
        assert status == 200
        assert body == b"document.title = 'Owner';"
        headers = login(server, token)
        for path in [
            "/private.txt",
            "/assets/../private.txt",
            "/assets/%2e%2e/private.txt",
            "/?token=not-accepted",
        ]:
            status, _, _ = exchange(server, path, headers=headers)
            assert status == 404
        status, _, _ = exchange(server, "/", headers={"Host": "evil.invalid"})
        assert status == 403


def test_build_symlink_is_rejected_before_binding(tmp_path: Path) -> None:
    build(tmp_path)
    (tmp_path / "assets/escape.js").symlink_to(tmp_path / "private.txt")
    with pytest.raises(ValueError, match="symlink"), running(studio_directory=tmp_path):
        pytest.fail("symlink build should never bind")


def test_oversized_build_is_rejected_before_loading(tmp_path: Path) -> None:
    build(tmp_path)
    with (tmp_path / "assets/huge.js").open("wb") as stream:
        _ = stream.truncate(MAX_FILE_BYTES + 1)
    with (
        pytest.raises(ValueError, match="byte limit"),
        running(studio_directory=tmp_path),
    ):
        pytest.fail("oversized build should never bind")
