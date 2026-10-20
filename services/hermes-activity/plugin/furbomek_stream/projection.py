"""Allowlisted public projection of Hermes tool calls."""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass
from typing import Final, Literal
from urllib.parse import urlsplit

type JsonValue = str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]
type JsonObject = dict[str, JsonValue]

Category = Literal["BROWSER", "COMPUTER", "WEB", "TERMINAL", "FILES", "AGENT"]
Status = Literal["ok", "error", "running"]


@dataclass(frozen=True, slots=True)
class PublicAction:
    """Safe, bounded tool description for the public activity stream."""

    category: Category
    action: str
    detail: str
    shutter: bool = False
    privacy_release: bool = False


_HOST: Final = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+$")
_KEY: Final = re.compile(r"^[A-Za-z0-9+_-]{1,24}$")
_SENSITIVE_HOST: Final = re.compile(r"(^|\.)(login|signin|auth|accounts|account|sso|id|vault|password|bank)\.")
_SAFE_KEYS: Final = frozenset(
    {
        "enter",
        "return",
        "tab",
        "escape",
        "esc",
        "backspace",
        "delete",
        "space",
        "home",
        "end",
        "pageup",
        "pagedown",
        "arrowup",
        "arrowdown",
        "arrowleft",
        "arrowright",
        "up",
        "down",
        "left",
        "right",
    }
)
_PUBLIC_PAGE: Final = "public page"
_PRIVATE_PAGE: Final = "private page"
_LOCAL_PAGE: Final = "local page"


def public_host(url: JsonValue) -> str:
    """Classify a URL without exposing its hostname."""
    if not isinstance(url, str) or len(url) > 4_096:
        return "—"
    try:
        parts = urlsplit(url.strip())
    except ValueError:
        return "—"
    if parts.scheme not in ("http", "https"):
        return _LOCAL_PAGE if parts.scheme in ("file", "about", "chrome", "data") else "—"
    host = (parts.hostname or "").lower().rstrip(".")
    if not host:
        return "—"
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        return _PRIVATE_PAGE
    if host in ("localhost",) or host.endswith((".local", ".lan", ".internal", ".ts.net", ".localhost")):
        return _PRIVATE_PAGE
    if not _HOST.fullmatch(host):
        return "—"
    return _PUBLIC_PAGE


def _navigation_is_sensitive(url: JsonValue) -> bool:
    """Classify navigation privacy from the URL without publishing its host."""
    if not isinstance(url, str) or len(url) > 4_096:
        return True
    try:
        parts = urlsplit(url.strip())
        host = (parts.hostname or "").lower().rstrip(".")
    except ValueError:
        return True
    if parts.scheme not in ("http", "https") or not host:
        return True
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        return True
    if host == "localhost" or host.endswith((".local", ".lan", ".internal", ".ts.net", ".localhost")):
        return True
    return _HOST.fullmatch(host) is None or _SENSITIVE_HOST.search(host + ".") is not None


def _count(value: JsonValue, noun: str) -> str:
    if isinstance(value, list):
        return f"{len(value)} {noun}{'' if len(value) == 1 else 's'}"
    return f"1 {noun}"


def _key(value: JsonValue) -> str:
    if not isinstance(value, str) or not _KEY.fullmatch(value):
        return "key"
    parts = re.split(r"[+-]", value.lower())
    return value if len(parts) == 1 and parts[0] in _SAFE_KEYS else "key"


def _text(value: JsonValue, allowed: tuple[str, ...]) -> str:
    return value if isinstance(value, str) and value in allowed else ""


def _computer(args: JsonObject) -> PublicAction:
    action = args.get("action")
    match action:
        case "capture":
            return PublicAction("COMPUTER", "looking at the screen", "screen hidden", shutter=True)
        case "click" | "double_click" | "right_click" | "middle_click":
            return PublicAction("COMPUTER", str(action).replace("_", " "), "on screen", shutter=True)
        case "type" | "set_value":
            return PublicAction("COMPUTER", "typing", "text hidden", shutter=True)
        case "key":
            keys = args.get("keys")
            first = keys[0] if isinstance(keys, list) and keys else keys
            return PublicAction("COMPUTER", "pressing", _key(first), shutter=True)
        case "scroll":
            return PublicAction(
                "COMPUTER", "scrolling", _text(args.get("direction"), ("up", "down", "left", "right")), shutter=True
            )
        case "drag":
            return PublicAction("COMPUTER", "dragging", "on screen", shutter=True)
        case "focus_app":
            return PublicAction("COMPUTER", "switching app", "app")
        case "list_apps" | "list_windows":
            return PublicAction("COMPUTER", "checking open apps", "")
        case "wait":
            return PublicAction("COMPUTER", "waiting", "")
        case _:
            return PublicAction("COMPUTER", "using the computer", "")


def project_tool(tool_name: str, args: JsonValue) -> PublicAction:
    """Project a tool call without copying arguments, results, or code."""
    values: JsonObject = args if isinstance(args, dict) else {}
    match tool_name:
        case "browser_navigate":
            host = public_host(values.get("url"))
            sensitive = _navigation_is_sensitive(values.get("url"))
            return PublicAction("BROWSER", "opening", host, shutter=sensitive, privacy_release=not sensitive)
        case "browser_snapshot":
            return PublicAction("BROWSER", "reading the page", "page hidden", shutter=True)
        case "browser_vision":
            return PublicAction("BROWSER", "looking at the page", "page hidden", shutter=True)
        case "browser_click":
            return PublicAction("BROWSER", "clicking", "page element", shutter=True)
        case "browser_type":
            return PublicAction("BROWSER", "typing", "text hidden", shutter=True)
        case "browser_press":
            return PublicAction("BROWSER", "pressing", _key(values.get("key")), shutter=True)
        case "browser_scroll":
            return PublicAction("BROWSER", "scrolling", _text(values.get("direction"), ("up", "down")), shutter=True)
        case "browser_back":
            return PublicAction("BROWSER", "going back", "history hidden", shutter=True)
        case "browser_history":
            return PublicAction("BROWSER", "checking history", "history hidden", shutter=True)
        case "browser_get_images":
            return PublicAction("BROWSER", "checking images", "page hidden", shutter=True)
        case "browser_console" | "browser_cdp" | "browser_exec":
            return PublicAction("BROWSER", "running page tools", "code hidden", shutter=True)
        case "browser_dialog":
            return PublicAction("BROWSER", "handling a dialog", "dialog hidden", shutter=True)
        case "browser_input" | "browser_fill_form" | "browser_select_option":
            return PublicAction("BROWSER", "entering input", "input hidden", shutter=True)
        case "browser_vault":
            return PublicAction("BROWSER", "using password vault", "screen hidden", shutter=True)
        case "computer_use":
            return _computer(values)
        case "web_search":
            return PublicAction("WEB", "searching the web", "query hidden")
        case "web_extract":
            return PublicAction("WEB", "reading", _count(values.get("urls"), "page"))
        case "terminal" | "process_manage" | "execute_code":
            return PublicAction("TERMINAL", "running a command", "command hidden")
        case "read_file" | "search_files":
            return PublicAction("FILES", "reading files", "")
        case "write_file" | "patch":
            return PublicAction("FILES", "editing files", "")
        case "vision_analyze" | "image_generate":
            return PublicAction("AGENT", "working with an image", "")
        case "delegate_task":
            return PublicAction("AGENT", "delegating a subtask", "")
        case _:
            return PublicAction("AGENT", "using a tool", "")


def outcome(status: JsonValue, error_type: JsonValue) -> Status:
    """Convert Hermes completion values to the bounded event status."""
    return "ok" if status == "ok" and not error_type else "error"
