"""Bounded immutable studio assets, supplied by the local server owner only."""

from collections.abc import Mapping
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from types import MappingProxyType

MAX_FILES = 64
MAX_FILE_BYTES = 4 * 1024 * 1024
MAX_TOTAL_BYTES = 16 * 1024 * 1024
CSP_DIRECTIVES = (
    "default-src 'none'",
    "script-src 'self'",
    "style-src 'self'",
    "font-src 'self'",
    "connect-src 'self'",
    "img-src 'self'",
    "base-uri 'none'",
    "object-src 'none'",
    "frame-ancestors 'none'",
    "form-action 'self'",
)
CSP = "; ".join(CSP_DIRECTIVES)

MIME = {
    ".js": "text/javascript",
    ".css": "text/css",
    ".ttf": "font/ttf",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
}


@dataclass(frozen=True, slots=True)
class Asset:
    """Already loaded bytes; request paths never reach the filesystem."""

    body: bytes
    content_type: str


def load_assets(directory: Path | None) -> Mapping[str, Asset]:
    """Accept only a real build directory without symlink traversal."""
    if directory is None:
        return MappingProxyType({})
    absolute = directory.absolute()
    if (
        any(path.is_symlink() for path in (absolute, *absolute.parents))
        or not absolute.is_dir()
    ):
        msg = "studio directory must be an existing non-symlink directory"
        raise ValueError(msg)
    paths = tuple(absolute.rglob("*"))
    if len(paths) > MAX_FILES or any(path.is_symlink() for path in paths):
        msg = "studio assets exceed count or contain symlinks"
        raise ValueError(msg)
    assets: dict[str, Asset] = {}
    total = 0
    for path in paths:
        relative = path.relative_to(absolute).as_posix()
        content_type = (
            "text/html"
            if relative == "index.html"
            else MIME.get(path.suffix)
            if relative.startswith("assets/")
            else None
        )
        if not path.is_file() or content_type is None:
            continue
        size = path.stat().st_size
        total += size
        if size > MAX_FILE_BYTES or total > MAX_TOTAL_BYTES:
            msg = "studio assets exceed byte limit"
            raise ValueError(msg)
        with path.open("rb") as stream:
            body = stream.read(MAX_FILE_BYTES + 1)
        if len(body) != size:
            msg = "studio asset changed during loading"
            raise ValueError(msg)
        assets["/" + relative] = Asset(body, content_type)
    if "/index.html" not in assets:
        msg = "studio build index missing"
        raise ValueError(msg)
    assets["/"] = assets["/index.html"]
    assets["/?mode=live"] = assets["/index.html"]
    return MappingProxyType(assets)


def serve_asset(
    handler: BaseHTTPRequestHandler, assets: Mapping[str, Asset], authority: str
) -> bool:
    """Serve exact immutable entries and same-origin CSP, otherwise decline."""
    asset = assets.get(handler.path)
    if asset is None:
        return False
    if handler.headers.get_all("Host") != [authority]:
        handler.send_error(HTTPStatus.FORBIDDEN)
        return True
    handler.send_response(HTTPStatus.OK)
    handler.send_header("Content-Type", asset.content_type)
    handler.send_header("Content-Length", str(len(asset.body)))
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("X-Content-Type-Options", "nosniff")
    handler.send_header("Content-Security-Policy", CSP)
    handler.end_headers()
    _ = handler.wfile.write(asset.body)
    return True
