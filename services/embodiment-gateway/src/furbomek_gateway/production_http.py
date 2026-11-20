"""Private loopback owner HTTP transport; no default controller or launcher."""

import json
import secrets
import socket
from http import HTTPStatus
from http.cookies import CookieError, SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import BoundedSemaphore, Lock
from typing import TYPE_CHECKING, cast, override

from pydantic import BaseModel, SecretStr, ValidationError

from .production_http_assets import Asset, load_assets, serve_asset
from .production_http_models import (
    ACTION,
    FramingRequest,
    ManualRequest,
    ProductionController,
    VisualRequest,
)
from .production_http_security import trusted_origin
from .production_http_sessions import Sessions

if TYPE_CHECKING:
    from collections.abc import Mapping

MAX_BODY = 32768
PREFIX = "/api/production/"


class OwnerHttpServer(ThreadingHTTPServer):
    """Loopback only, bounded request workers and serialized controller calls."""

    def __init__(  # noqa: PLR0913 - explicit bounded transport configuration
        self,
        controller: ProductionController,
        bootstrap: SecretStr,
        port: int = 0,
        *,
        session_ttl: int = 900,
        session_limit: int = 8,
        studio_directory: Path | None = None,
    ) -> None:
        """Caller owns serve_forever/shutdown/server_close and controller lifetime."""
        self.assets: Mapping[str, Asset] = load_assets(studio_directory)
        self.controller: ProductionController = controller
        self.sessions: Sessions = Sessions(bootstrap, session_ttl, session_limit)
        self.operation: Lock = Lock()
        self.workers: BoundedSemaphore = BoundedSemaphore(8)
        super().__init__(("127.0.0.1", port), OwnerHandler)
        self.authority: str = f"127.0.0.1:{self.server_port}"
        self.origin: str = f"http://{self.authority}"

    @override
    def get_request(self) -> tuple[socket.socket, tuple[str, int]]:
        connection, address = cast(
            "tuple[socket.socket, tuple[str, int]]", super().get_request()
        )
        connection.settimeout(3)
        return connection, address

    @override
    def process_request(
        self,
        request: socket.socket | tuple[bytes, socket.socket],
        client_address: tuple[str, int],
    ) -> None:
        if not self.workers.acquire(blocking=False):
            self.shutdown_request(request)
            return
        super().process_request(request, client_address)

    @override
    def process_request_thread(
        self,
        request: socket.socket | tuple[bytes, socket.socket],
        client_address: tuple[str, int],
    ) -> None:
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.workers.release()


class OwnerHandler(BaseHTTPRequestHandler):
    """Reject origin/host, oversized, unknown and stale requests before dispatch."""

    @property
    def owner(self) -> OwnerHttpServer:
        """Narrow the stdlib mutable server reference at its boundary."""
        if not isinstance(self.server, OwnerHttpServer):
            msg = "owner HTTP server required"
            raise TypeError(msg)
        return self.server

    @override
    def log_message(self, format: str, *args: str) -> None:
        """Never log request paths, credentials or private operation payloads."""

    def reply(
        self,
        status: HTTPStatus,
        payload: BaseModel | dict[str, str],
        cookie: str | None = None,
    ) -> None:
        """Send only private JSON with no cache or cross-origin grants."""
        body = (
            payload.model_dump_json().encode()
            if isinstance(payload, BaseModel)
            else json.dumps(payload).encode()
        )
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header(
            "Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'"
        )
        self.send_header("Connection", "close")
        if cookie is not None:
            self.send_header(
                "Set-Cookie",
                "; ".join(
                    (
                        f"production_owner={cookie}",
                        "HttpOnly",
                        "SameSite=Strict",
                        "Path=/api/production/",
                        f"Max-Age={self.owner.sessions.ttl}",
                    )
                ),
            )
        self.end_headers()
        _ = self.wfile.write(body)
        self.close_connection: bool = True

    def refuse(self, status: HTTPStatus, reason: str) -> None:
        """Bounded generic rejection; never return controller exception text."""
        self.reply(status, {"error": reason})

    def trusted(self) -> bool:
        """Require exact bound origin even for reads; refuse navigation."""
        if not trusted_origin(
            self.headers, self.owner.authority, self.owner.origin, self.command
        ):
            self.refuse(HTTPStatus.FORBIDDEN, "origin")
            return False
        return True

    def authenticated(self, *, mutation: bool) -> bool:
        """Cookie identity plus session-bound CSRF for every mutation."""
        cookies: SimpleCookie = SimpleCookie()
        try:
            cookies.load(self.headers.get("Cookie", ""))
        except CookieError:
            self.refuse(HTTPStatus.UNAUTHORIZED, "session")
            return False
        morsel = cookies.get("production_owner")
        session = self.owner.sessions.find(morsel.value if morsel else "")
        if session is None:
            self.refuse(HTTPStatus.UNAUTHORIZED, "session")
            return False
        if mutation and not secrets.compare_digest(
            self.headers.get("X-CSRF-Token", "").encode(), session.csrf.encode()
        ):
            self.refuse(HTTPStatus.FORBIDDEN, "csrf")
            return False
        return True

    def body(self) -> bytes | None:
        """Read one small JSON body, rejecting ambiguous HTTP framing."""
        lengths = self.headers.get_all("Content-Length", [])
        if (
            len(lengths) != 1
            or len(lengths[0]) > len(str(MAX_BODY))
            or not lengths[0].isdecimal()
            or not 0 < int(lengths[0]) <= MAX_BODY
        ):
            self.refuse(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "body-limit")
            return None
        if self.headers.get("Content-Type") != "application/json":
            self.refuse(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "content-type")
            return None
        result = self.rfile.read(int(lengths[0]))
        if len(result) != int(lengths[0]):
            self.refuse(HTTPStatus.BAD_REQUEST, "body")
            return None
        return result

    def do_GET(self) -> None:
        """Serve configured assets or authenticated status, with exact path lookup."""
        if serve_asset(self, self.owner.assets, self.owner.authority):
            return
        if not self.trusted() or not self.authenticated(mutation=False):
            return
        if self.path != PREFIX + "status":
            self.refuse(HTTPStatus.NOT_FOUND, "route")
            return
        self.dispatch(None)

    def do_POST(self) -> None:
        """Bootstrap or closed typed operation; no arbitrary route execution."""
        if not self.trusted():
            return
        if self.path == PREFIX + "session":
            body = self.body()
            if body != b"{}":
                if body is not None:
                    self.refuse(HTTPStatus.BAD_REQUEST, "bootstrap-body")
                return
            session = self.owner.sessions.create(self.headers.get("Authorization", ""))
            if session is None:
                self.refuse(HTTPStatus.UNAUTHORIZED, "bootstrap")
            else:
                self.reply(HTTPStatus.OK, {"csrf": session[1].csrf}, session[0])
            return
        if not self.authenticated(mutation=True):
            return
        if self.path != PREFIX + "action":
            self.refuse(HTTPStatus.NOT_FOUND, "route")
            return
        if (body := self.body()) is not None:
            self.dispatch(body)

    def dispatch(self, body: bytes | None) -> None:
        """Serialize HTTP operations; controller also fences other transports."""
        if not self.owner.operation.acquire(blocking=False):
            self.refuse(HTTPStatus.CONFLICT, "busy")
            return
        try:
            state = self.owner.controller.status()
            if body is None:
                self.reply(HTTPStatus.OK, state)
                return
            request = ACTION.validate_json(body)
            if request.epoch != state.epoch or request.revision != state.revision:
                self.refuse(HTTPStatus.CONFLICT, "stale")
                return
            dispatching = request.action in {
                "apply",
                "revert",
                "visual-apply",
                "framing-apply",
                "framing-manual",
            }
            if dispatching and state.health != "fresh":
                self.refuse(HTTPStatus.CONFLICT, state.health)
                return
            if (
                isinstance(request, VisualRequest)
                and request.action == "visual-apply"
                and not state.visual_available
            ) or (
                isinstance(request, (FramingRequest, ManualRequest))
                and dispatching
                and not state.framing_available
            ):
                self.refuse(HTTPStatus.CONFLICT, "unavailable")
                return
            result = self.owner.controller.execute(request)
            self.reply(
                HTTPStatus.OK if result.outcome == "accepted" else HTTPStatus.CONFLICT,
                result,
            )
        except ValidationError:
            self.refuse(HTTPStatus.BAD_REQUEST, "schema")
        except Exception:  # noqa: BLE001 # noqa: BROAD_EXCEPT_OK - HTTP error boundary
            self.refuse(HTTPStatus.SERVICE_UNAVAILABLE, "unavailable")
        finally:
            self.owner.operation.release()
